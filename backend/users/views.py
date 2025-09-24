from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from .models import User, Follow
from rest_framework.response import Response
from .serializers import UserSerializer, FollowSerializer
from users.utils import send_mail
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    """Доп. логика для создания пользователя"""
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Пользователь и код подтверждения"""
        user = serializer.save()
        send_mail(
            subject="Добро пожаловать!",
            message="Вы успешно зарегистрированы!",
            from_email=None,
            recipient_list=[user.email],
        )
        

class FollowViewSet(viewsets.ModelViewSet):
    """Вьюсет модели подписок"""
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
       return Follow.objects.filter(user=self.request.user)
    
    def perform_crate(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Подписки пользователя"""
        follows = self.get_queryset()
        serializer = self.get_serializer(follows, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """Подписаться / Отписаться"""
        User = get_user_model
        author = get_object_or_404(User, pk=pk)

        if request.method == 'POST':
            serializer =self.get_serializer(data={'author': author.id})
            serializer.is_valid(raise_exteption=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            follow = get_object_or_404(Follow, user=request.user, author=author)
            follow.delete
            return Response(status=status.HTTP_204_NO_CONTENT)