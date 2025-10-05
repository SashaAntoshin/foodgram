from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.paginations import CustomPagination
from api.serializers import (
    AvatarUpdateSerializer,
    FollowSerializer,
    RecipeReadSerializer,
    SubscriptionSerializer,
)
from recipes.models import Favorite

from .models import Follow, User
from .serializers import (
    UserListSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        return UserListSerializer

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Подписка/отписка на автора."""
        author = self.get_object()
        user = request.user

        if request.method == "POST":
            follow_serializer = FollowSerializer(
                data={"author": author.id}, context={"request": request}
            )
            follow_serializer.is_valid(raise_exception=True)
            follow_serializer.save(user=user)
            serializer = SubscriptionSerializer(
                author,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            deleted_count, _ = Follow.objects.filter(
                user=user, author=author
            ).delete()

            if deleted_count == 0:
                return Response(
                    {"detail": "Подписка не найдена"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Список моих подписок."""
        user = request.user
        subscribed_authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(subscribed_authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class UserListView(APIView):
    """Отдельный вью только для списка пользователей."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = User.objects.all()
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class MeView(APIView):
    """Вью для user/me."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserListSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)


class UserAvatarView(APIView):
    """Вью для аватара."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self, request):
        """Обновление."""
        serializer = AvatarUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        """Удаление."""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=204)


class ChangePassword(APIView):
    """Смена пароля."""

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


class FollowViewSet(viewsets.ModelViewSet):
    """Вьюсет модели подписок."""

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
        """Подписки пользователя."""
        follows = self.get_queryset()
        serializer = self.get_serializer(follows, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"])
    def subscribe(self, request, pk=None):
        """Подписаться / Отписаться."""
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
    """Список избранного."""

    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.select_related(
            "recipe", "recipe__author"
        ).filter(user=self.request.user)
