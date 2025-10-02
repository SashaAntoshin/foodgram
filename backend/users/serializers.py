import re

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.authtoken.models import Token

"""Сериализаторы для пользователей"""

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""

    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "password",
        )
        extra_kwargs = {"password": {"write_only": True}}
        username = serializers.CharField(max_length=150)

    def get_is_subscribed(self, obj):
        request_user = self.context["request"].user
        if request_user.is_authenticated:
            if obj == request_user:
                return False
            return obj.followers.filter(user=request_user).exists()
        return False

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            return (
                request.build_absolute_uri(obj.avatar.url)
                if request
                else obj.avatar.url
            )
        return None

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Регистрация, валидация username и email"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
        )
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_username(self, value):
        if not re.match(r"^[\w.@+-]+\Z", value):
            raise serializers.ValidationError(
                "Разрешены только буквы, цифры и символы @/./+/-/_"
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким username уже существует."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Token.objects.get_or_create(user=user)
        return user


class UserListSerializer(serializers.ModelSerializer):
    """Сериализатор информации о пользователе"""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        return False

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        """Рецепты пользователя с ограничением через recipes_limit"""
        request = self.context.get("request")
        recipes_limit = None

        if request:
            recipes_limit = request.query_params.get("recipes_limit")

        recipes = obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]

        from api.serializers import RecipeShortSerializer

        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_avatar(self, obj):
        """Вернём ссылку на аватар, если он есть"""
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
