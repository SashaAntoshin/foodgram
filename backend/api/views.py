from rest_framework import viewsets

from users.models import User
from recipes.models import Recipe, Ingredient, Tag
from api.serializers import (
    UserSerializer,
    RecipeSerializer,
    IngredientSerializer,
    TagSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""
    queryset = User.objects.all()
    serializer_class = UserSerializer


class RicepeViewSet(viewsets.ModelViewSet):
    """Вьюсет для Рецептов"""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer


class IngerientViewSet(viewsets.ModelViewSet):
    """Вьюсет для Ингридиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для Тег"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
