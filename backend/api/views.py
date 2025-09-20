from rest_framework import viewsets, permissions

from users.models import User
from recipes.models import Recipe, Ingredient, Tag
from api.serializers import (
    UserSerializer,
    RecipeSerializer,
    IngredientSerializer,
    TagSerializer
)
from api.permissions import IsAdmin, IsAdminOrReadOnly, IsAuthorOrIsAdmin


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    """Доп. логика для создания пользователя"""
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()
        


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
