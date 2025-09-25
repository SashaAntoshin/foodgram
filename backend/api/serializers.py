from rest_framework import serializers
from django.core.validators import RegexValidator
from users.models import User, Follow
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (
    Recipe,
    IngredientsInRecipe,
    Ingredient,
    Tag,
    Favorites,
    ShoppingBasket,
)
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели юзера"""
    # avatar = Base64ImageField(required=False)
    # is_subscribed = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name',
            'email', 'username', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}
        username = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
                message='Недопустимые символы в username',
                code='invalid_username'
            )
        ]
    )
    
    def get_is_subscribed(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            if obj == request_user:
                return False
            return obj.followers.filter(user=request_user).exists()
        return False

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None

    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    

class AvatarUpdateSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model= User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Тег"""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиент"""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиентов в рецепте"""
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = IngredientsInRecipe
        fields = ('ingredient', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели Рецепт"""
    image = serializers.ImageField()
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
    )
    ingredients_detail = IngredientInRecipeSerializer(
        source='ingredients_amounts',
        many=True,
        read_only=True,
    )

    class Meta:
        model = Recipe
        fields = (
            'author', 'name', 'image',
            'description', 'pub_date', 'cooking_time',
            'ingredients', 'tags',
        )

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )
        recipe.tags.set(tags)

        for item in ingredients:
            IngredientsInRecipe.objects.create(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=item['id']),
                amount=item['amount'],
            )
        return recipe

    def validate(self, attrs):
        raw_list = attrs.get('ingredients')
        if not isinstance(raw_list, list) or len(raw_list) == 0:
            raise serializers.ValidationError({
                'ingredients': 'Список ингредиентов обязателен и не может быть пустым'
            })

        normalized = []
        ingredient_ids = []
        bad_shape = []
        bad_amount = []

        for index, item in enumerate(raw_list):
            if (
                not isinstance(item, dict)
                or 'id' not in item
                or 'amount' not in item
            ):
                bad_shape.append(index)
                continue

            ing_id = item.get('id')
            amt = item.get('amount')

            if isinstance(amt, str) and amt.isdigit():
                amt = int(amt)

            if not isinstance(amt, int) or amt < 1:
                bad_amount.append((index, amt))
                continue

            ingredient_ids.append(ing_id)
            normalized.append({'id': ing_id, 'amount': amt})

        if bad_shape:
            raise serializers.ValidationError({
                'ingredients': f'Некорректная структура: {bad_shape}'
            })

        if bad_amount:
            details = ', '.join([f'#{pos}={val}' for pos, val in bad_amount])
            raise serializers.ValidationError({
                'ingredients': (
                    f'Некорректное количество у позиций: {details}. '
                    f'Требуется целое число'
                )
            })

        id_counter = {}
        for ing_id in ingredient_ids:
            id_counter[ing_id] = id_counter.get(ing_id, 0) + 1
        repeated_ids = sorted([
            ing_id for ing_id, cnt in id_counter.items() if cnt > 1
        ])
        if repeated_ids:
            readable = ', '.join(str(x) for x in repeated_ids)
            raise serializers.ValidationError({
                'ingredients': f'Повторяются ингредиенты с id: {readable}'
            })

        existing = set(
            Ingredient.objects.filter(id__in=ingredient_ids)
            .values_list('id', flat=True)
        )
        missing = sorted(set(ingredient_ids) - existing)
        if missing:
            raise serializers.ValidationError({
                'ingredients': f'Не найдены ингредиенты с id: {missing}'
            })

        tags_value = attrs.get('tags')
        if isinstance(tags_value, list) and len(tags_value) == 0:
            raise serializers.ValidationError({
                'tags': 'Нужно указать хотя бы один тег'
            })

        attrs['ingredients'] = normalized
        return attrs


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для Избранного"""
    class Meta:
        model = Favorites
        fields = ('user', 'recipe', 'added_at')


class ShopingBasketSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины"""

    class Meta:
        model = ShoppingBasket
        fields = '__all_'


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор модели Подписок"""
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
    )
    author = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def validate_author(self, value):
        """Проверка подписок"""
        user = self.context['request'].user
        if value == user:
            raise serializers.ValidationError(
                'Подписаться на себя невозможно'
            )
        if Follow.objects.filter(user=user, author=value).exists():
            raise serializers.ValidationError(
                'Вы уже подписались на этого автора ранее'
            )
        return value
