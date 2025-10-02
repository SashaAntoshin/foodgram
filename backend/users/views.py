from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    UserSerializer,
    UserListSerializer,
    UserRegistrationSerializer,
)
from api.serializers import (
    FollowSerializer,
    SubscriptionSerializer,
    AvatarUpdateSerializer,
    RecipeReadSerializer,
)

from users.utils import send_mail
from recipes.models import Favorites

from .models import Follow, User
from .paginations import CustomPagination


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination
    """Доп. логика для создания пользователя"""

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        """Пользователь и код подтверждения"""
        user = serializer.save()
        send_mail(
            subject="Добро пожаловать!",
            message="Вы успешно зарегистрированы!",
            from_email=None,
            recipient_list=[user.email],
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Подписка/отписка на автора"""
        author = self.get_object()
        user = request.user

        if request.method == "POST":
            if user == author:
                return Response(
                    {"detail": "Нельзя подписаться на себя"}, status=400
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response({"detail": "Вы уже подписаны"}, status=400)
            Follow.objects.create(user=user, author=author)

            recipes_limit = request.query_params.get("recipes_limit")
            try:
                recipes_limit = int(recipes_limit)
            except (TypeError, ValueError):
                recipes_limit = None

            serializer = SubscriptionSerializer(
                author,
                context={"request": request, "recipes_limit": recipes_limit},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            follow = Follow.objects.filter(user=user, author=author).first()
            if not follow:
                return Response({"detail": "Подписка не найдена"}, status=400)
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Список моих подписок"""
        user = request.user
        subscribed_authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(subscribed_authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class UserListView(APIView):
    """Отдельный вью только для списка пользователей"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = User.objects.all()
        serializer = UserLIstSerializer(users, many=True)
        return Response(serializer.data)


class MeView(APIView):
    """Вью для user/me"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserLIstSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)


class UserAvatarView(APIView):
    """Вью для аватара"""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self, request):
        """Обновление"""
        serializer = AvatarUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        """Удаление"""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=204)


class ChangePassword(APIView):
    """Смена пароля"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not user.check_password(current_password):
            return Response(
                {"detail": "Неверный текущий пароль"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    """Вью для выхода и удаления токена"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Удаление токена"""
        try:
            if request.auth:
                request.auth.delete()
            else:
                from rest_framework.authtoken.models import Token

                Token.objects.filter(user=request.user).delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception:
            return Response(
                {"error": "Ошибка входа"}, status=status.HTTP_400_BAD_REQUEST
            )


class FollowViewSet(viewsets.ModelViewSet):
    """Вьюсет модели подписок"""

    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Отключаем базовый POST /follows/ в пользу action subscribe."""
        return Response(
            {"detail": "Используйте POST /follows/subscribe/{author_id}/"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"])
    def subscriptions(self, request):
        """Подписки пользователя"""
        follows = self.get_queryset()
        serializer = self.get_serializer(follows, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"])
    def subscribe(self, request, pk=None):
        """Подписаться / Отписаться"""
        User = get_user_model()
        author = get_object_or_404(User, pk=pk)

        if request.method == "POST":
            serializer = self.get_serializer(data={"author": author.id})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == "DELETE":
            follow = get_object_or_404(
                Follow, user=request.user, author=author
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListView(generics.ListAPIView):
    """Список избранного"""

    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorites.objects.select_related(
            "recipe", "recipe__author"
        ).filter(user=self.request.user)
