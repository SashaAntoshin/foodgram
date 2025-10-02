from users.serializers import UserListSerializer

from rest_framework import serializers
from django.contrib.auth import get_user_model

from recipes.models import (
    Favorites,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingBasket,
    Tag,
)
from users.models import Follow
import base64
from django.core.files.base import ContentFile


User = get_user_model()


class RecipeShortSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор пецептов"""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Тег"""

    class Meta:
        model = Tag
        fields = "__all__"


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
            return Favorites.objects.filter(
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

    """Валидация тегов и ингредиентов"""

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым."
            )
        ids = [i.get("id") for i in value]
        if None in ids:
            raise serializers.ValidationError(
                "Каждый ингредиент должен содержать id."
            )
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )
        for ing in value:
            if "amount" not in ing:
                raise serializers.ValidationError(
                    "Каждый ингредиент должен содержать amount."
                )
            if int(ing["amount"]) <= 0:
                raise serializers.ValidationError(
                    "Количество должно быть больше 0."
                )
        existing_ids = set(
            Ingredient.objects.filter(id__in=ids).values_list("id", flat=True)
        )
        missing = set(ids) - existing_ids
        if missing:
            raise serializers.ValidationError(
                f"Не найдены ингредиенты с id: {sorted(missing)}"
            )
        return value

    def validate(self, data):
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

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        for ing in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=recipe, ingredient_id=ing["id"], amount=ing["amount"]
            )
        return recipe

    def update(self, instance, validated_data):
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

        instance.name = validated_data.get("name", instance.name)
        instance.text = validated_data.get("text", instance.text)
        instance.cooking_time = validated_data.get(
            "cooking_time", instance.cooking_time
        )
        if "image" in validated_data:
            instance.image = validated_data["image"]
        instance.save()

        instance.tags.set(tags_data)
        instance.ingredients_amounts.all().delete()
        for ing in ingredients_data:
            IngredientsInRecipe.objects.create(
                recipe=instance, ingredient_id=ing["id"], amount=ing["amount"]
            )

        return instance


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для Избранного"""

    class Meta:
        model = Favorites
        fields = ("user", "recipe", "added_at")


class ShopingBasketSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины"""

    class Meta:
        model = ShoppingBasket
        fields = "__all__"


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
            raise serializers.ValidationError(
                "Подписаться на себя " "невозможно"
            )
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
        recipes_limit = (
            request.query_params.get("recipes_limit") if request else None
        )
        if recipes_limit and recipes_limit.isdigit():
            recipes_limit_int = int(recipes_limit)
            recipes = recipes[:recipes_limit_int]
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
