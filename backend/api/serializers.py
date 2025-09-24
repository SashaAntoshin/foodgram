from rest_framework import serializers
from users.models import User
from recipes.models import (
    Recipe,
    IngredientsInRecipe,
    Ingredient,
    Tag,
    Favorites,
    ShoppingBasket
)

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели юзера"""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name',
                  'email', 'username', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Тег"""
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиент"""
    class Meta:
        model = Ingredient
        fields = ('name', 'unit')


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
        many=True
    )
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    ingredients_detail = IngredientInRecipeSerializer(
        source='ingredients_amounts',
        many=True,
        read_only=True
    )

    class Meta:
        model = Recipe
        fields = ('author', 'name', 'image', 'description', 'pub_date',
                  'time', 'ingredients', 'tags')

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user, **validated_data)
        recipe.tags.set(tags)

        for item in ingredients:
            IngredientsInRecipe.objects.create(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=item['id']),
                amount=item['amount']
            )
        return recipe

    def validate(self, attrs):
        ingredients_list = attrs.get('ingredients')
        if not isinstance(ingredients_list, list) or len(ingredients_list) == 0:
            raise serializers.ValidationError(
                'Cписок не может быть пустым'
            )

        ingredients = attrs['ingredients']
        ingredient_ids = []
        bad_positions = []
        for index, item in enumerate(ingredients):
            if not isinstance(item, dict) or 'id' not in item:
                bad_positions.append(index)
                continue
            ingredient_ids.append(item['id'])

        if bad_positions:
            raise serializers.ValidationError(
                {'ingredients': f'Некорректные элементы на позициях: {bad_positions}'}
            )

        id_counter = {}
        for ing_id in ingredient_ids:
            id_counter[ing_id] = id_counter.get(ing_id, 0) + 1
        repeated_ids = sorted(
            [ing_id for ing_id, cnt in id_counter.items() if cnt > 1])
        if repeated_ids:
            readable = ', '.join(str(x) for x in repeated_ids)
            raise serializers.ValidationError(
                {'ingredients': f'Повторяются ингредиенты с id: {readable}'}
            )
        return attrs


class FavoritesAndBasketSerializer(serializers.ModelSerializer):
    """Сериализатор для Избранного"""
    class Meta:
        model = Favorites
        fields = ('favorite_cook', 'recipe', 'added_at')
