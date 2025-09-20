"""Кастомные сериализаторы для djoser"""
from djoser.serializers import UserCreateSerializer, UserSerializer
from .models import User


class DjoserUserCreateSerializer(UserCreateSerializer):
    """Сериализатор создания пользователя"""
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        ]
        extra_kwargs = {'password': {'write_only': True}}


class DjoserUserSerializer(UserSerializer):
    """Сериализатор пользователя для настроек Djoser"""
    class Meta(UserSerializer.Meta):
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']
