from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .filters import RecipeFilter
from api.serializers import (
    FavoritesSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingBasket,
    Tag,
)

from .paginations import CustomPagination
from .permissions import IsAuthorOrIsAdmin, IsAuthorOrReadOnly


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов"""

    queryset = Recipe.objects.select_related("author").prefetch_related(
        "tags", "ingredients_amounts__ingredient"
    )
    permission_classes = [IsAuthorOrIsAdmin, IsAuthorOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        self.instance = serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        self.instance = serializer.save()

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        read_serializer = RecipeReadSerializer(
            self.instance, context={"request": self.request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = RecipeWriteSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = RecipeReadSerializer(
            instance, context={"request": request}
        )
        return Response(read_serializer.data)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Получение ссылки на рецепт."""
        recipe = self.get_object()
        recipe_url = request.build_absolute_uri(f"/recipes/{recipe.id}/")

        return Response({"short-link": recipe_url}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == "POST":
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"detail": "Рецепт уже в избранном"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            favorite_serializer = FavoritesSerializer(
                data={"recipe": recipe.id}, context={"request": request}
            )
            favorite_serializer.is_valid(raise_exception=True)
            favorite_serializer.save(user=user)
            serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        delete_favor = Favorite.objects.filter(
            user=user, recipe=recipe
        ).exists()
        if not delete_favor:
            return Response(
                {"detail": "Рецет не найден в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Favorite.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        """Добавление и удаление рецепта в корзину."""
        recipe = self.get_object()
        user = request.user

        if request.method == "POST":
            if ShoppingBasket.objects.filter(
                user=user, recipe=recipe
            ).exists():
                return Response(
                    {"detail": "Рецепт уже в корзине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingBasket.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            """Удаление из корзины."""
            cart_exists = ShoppingBasket.objects.filter(
                user=user, recipe=recipe
            ).exists()
            if not cart_exists:
                return Response(
                    {"detail": "Рецепт не найден в корзине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingBasket.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок с оптимизацией запросов."""
        user = request.user
        ingredients = (
            IngredientsInRecipe.objects.filter(
                recipe__in_shopping_basket__user=user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )
        shopping_list = "Список покупок:\n\n"
        for item in ingredients:
            name = item["ingredient__name"]
            amount = item["total_amount"]
            unit = item["ingredient__measurement_unit"]
            shopping_list += f"- {name} - {amount} {unit}\n"
        shopping_list += f"\nВсего ингредиентов: {len(ingredients)}"
        response = HttpResponse(
            shopping_list, content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для Ингридиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ("^name",)

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для Тег"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = []
    pagination_class = None
