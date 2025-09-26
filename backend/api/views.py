from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from recipes.models import Recipe, Ingredient, Tag, Favorites
from .pagination import CustomPagination
from api.serializers import (
    RecipeSerializer,
    IngredientSerializer,
    TagSerializer,
    FavoritesSerializer
)
from .permissions import IsAdminOrReadOnly, IsAuthorOrIsAdmin


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для Рецептов"""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # ПРОВЕРКА: пользователь может обновлять только свои рецепты
        if instance.author != request.user:
            return Response(
                {'detail': 'У вас нет прав для изменения этого рецепта'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """
        Эндпоинт для получения ссылки на рецепт
        """
        recipe = self.get_object()
        
        # Генерируем ссылку на рецепт
        recipe_url = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        
        return Response({
            'link': recipe_url
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=('post', 'delete'), permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if Favorites.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Favorites.objects.create(user=user, recipe=recipe)
            return Response({'detail': 'Добавлено в избранное'}, status=status.HTTP_201_CREATED)

        favor = Favorites.objects.filter(user=user, recipe=recipe).first()
        if not favor:
            return Response({'detail': 'Рецепт не найден'}, status=status.HTTP_400_BAD_REQUEST)
        favor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListView(generics.ListAPIView):
    """Список избранного"""
    serializer_class = FavoritesSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorites.objects.select_related('recipe', 'recipe__author').filter(user=self.request.user)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для Ингридиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset



class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для Тег"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = []
    pagination_class = None
