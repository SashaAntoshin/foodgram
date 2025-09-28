from django.contrib.auth import get_user_model
from users.models import Follow, User
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
import base64
import re
from django.core.files.base import ContentFile

"""Сериализаторы для пользователей"""

from users.models import Follow, User

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели юзера"""

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
        write_only=True, required=True, style={"input_type": "password"}
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
        """Создание пользователя с хэшированием пароля"""
        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user

    def validate_email(self, value):
        """Валидация email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        from rest_framework.authtoken.models import Token

        Token.objects.get_or_create(user=user)
        return user


class UserLIstSerializer(serializers.ModelSerializer):
    """Сериализатор информации пользователя"""

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
        """Вернем ссылку на аватар, если он есть"""
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class Base64ImageField(serializers.ImageField):
    """Конвертация картинки для сериализатора рецептов"""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]
                decoded_file = base64.b64decode(imgstr)
                file_name = f"recipe_image.{ext}"
                data = ContentFile(decoded_file, name=file_name)

            except Exception as e:
                raise serializers.ValidationError(
                    "Некорректный формат изображения"
                )

        return super().to_internal_value(data)


class AvatarUpdateSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ("avatar",)

class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор модели Подписок"""

    user = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
    )
    author = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = "__all__"
        read_only_fields = ("user", "created_at")

    def validate_author(self, value):
        """Проверка подписок"""
        user = self.context["request"].user
        if value == user:
            raise serializers.ValidationError("Подписаться на себя невозможно")
        if Follow.objects.filter(user=user, author=value).exists():
            raise serializers.ValidationError(
                "Вы уже подписались на этого автора ранее"
            )
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор списка подписок (/subscriptions/)."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.follower.filter(author=obj).exists()
        return False

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        request = self.context.get("request")
        recipes_limit = self.context.get("recipes_limit")
        if recipes_limit:
            recipes = recipes[:recipes_limit]
        return [
            {
                "id": recipe.id,
                "name": recipe.name,
                "image": (
                    request.build_absolute_uri(recipe.image.url)
                    if recipe.image
                    else None
                ),
                "cooking_time": recipe.cooking_time,
            }
            for recipe in recipes
        ]

    def get_recipes_count(self, obj):
        return obj.recipes.count()
