from rest_framework import serializers

from users.models import User
from recipes.models import Recipe, Tag, Ingredient, IngredientsInRecipe


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели юзера"""
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'username')


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


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели Рецепт"""
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientSerializer(
        source='ingredients_amounts',
        read_only=True,
        many=True
	)

    class Meta:
        model = Recipe
        fields = ('author', 'name', 'image', 'description', 'pub_date',
                  'time', 'ingredients', 'tags')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ингридиентов в рецепте"""
    ingredient = IngredientSerializer(read_only=True)
    
    class Meta:
        model = IngredientsInRecipe
        fields = ('ingredient', 'amount')
