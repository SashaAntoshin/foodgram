from rest_framework import viewsets

from recipes.models import Recipe, Ingredient, Tag
from api.serializers import (
    RecipeSerializer,
    IngredientSerializer,
    TagSerializer
)
from .permissions import IsAdminOrReadOnly, IsAuthorOrIsAdmin



class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для Рецептов"""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrIsAdmin]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class IngerientViewSet(viewsets.ModelViewSet):
    """Вьюсет для Ингридиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для Тег"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
