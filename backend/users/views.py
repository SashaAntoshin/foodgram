from rest_framework import viewsets, permissions, status
from .paginations import CustomPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from .models import User, Follow
from rest_framework.response import Response
from api.serializers import UserSerializer, FollowSerializer, AvatarUpdateSerializer, UserLIstSerializer
from users.utils import send_mail
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination
    """Доп. логика для создания пользователя"""

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserLIstSerializer

    def perform_create(self, serializer):
        """Пользователь и код подтверждения"""
        user = serializer.save()
        send_mail(
            subject="Добро пожаловать!",
            message="Вы успешно зарегистрированы!",
            from_email=None,
            recipient_list=[user.email],
        )

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
        serializer = UserLIstSerializer(request.user, context={'request': request})
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
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not user.check_password(current_password):
            return Response({"detail": "Неверный текущий пароль"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    """Вью для выхода и удаления токена"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Удаление токена """
        try:
            if request.auth:
                request.auth.delete()
            else:
                from rest_framework.authtoken.models import Token
                Token.objects.filter(user=request.user).delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {'error': 'Ошибка входа'},
                status=status.HTTP_400_BAD_REQUEST
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
            {'detail': 'Используйте POST /follows/subscribe/{author_id}/'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Подписки пользователя"""
        follows = self.get_queryset()
        serializer = self.get_serializer(follows, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """Подписаться / Отписаться"""
        User = get_user_model()
        author = get_object_or_404(User, pk=pk)

        if request.method == 'POST':
            serializer = self.get_serializer(data={'author': author.id})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            follow = get_object_or_404(
                Follow, user=request.user, author=author)
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
