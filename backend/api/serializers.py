import base64
import re

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from recipes.models import (Favorite, Ingredient, IngredientsInRecipe, Recipe,
                            ShoppingBasket, Tag)
from users.models import Follow

User = get_user_model()


"""Сериализаторы для пользователей."""


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя."""

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
    """Регистрация, валидация username и email."""

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
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Token.objects.get_or_create(user=user)
        return user


class UserListSerializer(serializers.ModelSerializer):
    """Сериализатор информации о пользователе."""

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

    def get_avatar(self, obj):
        """Вернём ссылку на аватар, если он есть."""
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class RecipeShortSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор пецептов"""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Тег"""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиент"""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = IngredientsInRecipe
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserListSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source="ingredients_amounts", many=True, read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        """Проверка избранного"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Проверка наличия рецепта в корзине"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return ShoppingBasket.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False


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

            except Exception:
                raise serializers.ValidationError(
                    "Некорректный формат изображения"
                )

        return super().to_internal_value(data)


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            "name",
            "image",
            "text",
            "cooking_time",
            "ingredients",
            "tags",
        )

    def validate_ingredients(self, value):
        """Валидация ингредиентов."""
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым."
            )

        ingredient_ids = [ingredient.get("id") for ingredient in value]

        if None in ingredient_ids:
            raise serializers.ValidationError(
                "Каждый ингредиент должен содержать id."
            )

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )

        for ingredient in value:
            if "amount" not in ingredient:
                raise serializers.ValidationError(
                    "Каждый ингредиент должен содержать amount."
                )
            if int(ingredient["amount"]) <= 0:
                raise serializers.ValidationError(
                    "Количество должно быть больше 0."
                )

        existing_ids = set(
            Ingredient.objects.filter(id__in=ingredient_ids).values_list(
                "id", flat=True
            )
        )
        missing_ids = set(ingredient_ids) - existing_ids

        if missing_ids:
            raise serializers.ValidationError(
                f"Не найдены ингредиенты с id: {sorted(missing_ids)}"
            )

        return value

    def validate(self, data):
        """Валидация тегов."""
        tags = data.get("tags")
        if not tags:
            raise serializers.ValidationError(
                {"tags": "Список тегов обязателен."}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {"tags": "Теги не должны повторяться."}
            )
        return data

    def _create_ingredients(self, recipe, ingredients_data):
        """Создание ингредиентов для рецепта (вспомогательный метод)."""
        ingredients_to_create = [
            IngredientsInRecipe(
                recipe=recipe,
                ingredient_id=ingredient["id"],
                amount=ingredient["amount"],
            )
            for ingredient in ingredients_data
        ]
        IngredientsInRecipe.objects.bulk_create(ingredients_to_create)

    def _set_tags_and_ingredients(self, recipe, tags_data, ingredients_data):
        """Едины метод для тегов и ингредиентов."""
        recipe.tags.set(tags_data)
        recipe.ingredients_amounts.all().delete()
        self._create_ingredients(recipe, ingredients_data)

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")

        recipe = Recipe.objects.create(**validated_data)
        self._set_tags_and_ingredients(recipe, tags_data, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        ingredients_data = validated_data.pop("ingredients", None)
        tags_data = validated_data.pop("tags", None)

        if ingredients_data is None:
            raise serializers.ValidationError(
                {"ingredients": "Поле обязательно при обновлении рецепта."}
            )
        if tags_data is None:
            raise serializers.ValidationError(
                {"tags": "Поле обязательно при обновлении рецепта."}
            )

        instance = super().update(instance, validated_data)
        self._set_tags_and_ingredients(instance, tags_data, ingredients_data)

        return instance


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для Избранного"""

    class Meta:
        model = Favorite
        fields = ("user", "recipe", "added_at")
        read_only_fields = ("user", "added_at")

    def create(self, validated_data):
        """Подставляем user из контекста"""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ShopingBasketSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины"""

    class Meta:
        model = ShoppingBasket
        fields = ("user", "recipe", "added_at")


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
        slug_field="id",
        queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = ("user", "author", "created_at")
        read_only_fields = ("user", "created_at")

    def validate_author(self, value):
        """Проверка подписок"""
        user = self.context["request"].user
        if value == user:
            raise serializers.ValidationError("Подписаться на себя невозможно")
        if Follow.objects.filter(user=user, author=value).exists():
            raise serializers.ValidationError(
                "Вы уже подписались на этого автора"
            )
        return value

    def create(self, validated_data):
        """Создание подписки"""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор списка подписок (/subscriptions/)."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True, default=0)

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
        recipes_limit = (
            request.query_params.get("recipes_limit") if request else None
        )
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]
        from api.serializers import RecipeShortSerializer

        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data
