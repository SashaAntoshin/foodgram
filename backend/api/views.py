from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import (
    FavoritesSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)
from recipes.models import Favorites, Ingredient, Recipe, ShoppingBasket, Tag

from .pagination import CustomPagination
from .permissions import IsAuthorOrIsAdmin, IsAuthorOrReadOnly


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrIsAdmin, IsAuthorOrReadOnly]
    pagination_class = CustomPagination
    filterset_fields = ["author", "tags"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_queryset(self):
        """Фильтрация по авторам и тегам"""
        queryset = super().get_queryset()
        author_id = self.request.query_params.get("author")
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        tags = self.request.query_params.getlist("tags")
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        return queryset

    def perform_create(self, serializer):
        self.instance = serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        read_serializer = RecipeReadSerializer(
            self.instance, context={"request": self.request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self.instance = serializer.save()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        recipe = self.get_object()
        return Response(
            {"link": f"http://{request.get_host()}/recipes/{recipe.id}/"},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        super().partial_update(request, *args, **kwargs)
        read_serializer = RecipeReadSerializer(
            self.instance, context={"request": self.request}
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Получение ссылки на рецепт"""
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
            if Favorites.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"detail": "Рецепт уже в избранном"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Favorites.objects.create(user=user, recipe=recipe)
            return Response(
                {"detail": "Добавлено в избранное"},
                status=status.HTTP_201_CREATED,
            )

        favor = Favorites.objects.filter(user=user, recipe=recipe).first()
        if not favor:
            return Response(
                {"detail": "Рецепт не найден"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        favor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        """Добавление и удаление рецепта в корзину"""
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
            return Response(
                {"detail": "Добавлено в корзину"},
                status=status.HTTP_201_CREATED,
            )
        elif request.method == "DELETE":
            """Удвление из корзины"""
            recipe_item = ShoppingBasket.objects.filter(
                user=user, recipe=recipe
            ).first()
            if not recipe_item:
                if not recipe_item:
                    return Response(
                        {"detail": "Рецепт не найден в корзине"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            recipe_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок"""
        user = request.user
        shopping_cart_items = ShoppingBasket.objects.filter(user=user)
        recipes = [item.recipe for item in shopping_cart_items]
        ingredients_dict = {}

        for recipe in recipes:
            for ingredient_amount in recipe.ingredients_amounts.all():
                ingredient = ingredient_amount.ingredient
                amount = ingredient_amount.amount

                key = (ingredient.name, ingredient.measurement_unit)
                if key in ingredients_dict:
                    ingredients_dict[key] += amount
                else:
                    ingredients_dict[key] = amount

        shopping_list = "Список покупок:\n\n"
        for (name, unit), amount in ingredients_dict.items():
            shopping_list += f"• {name} - {amount} {unit}\n"

        shopping_list += f"\nВсего ингредиентов: {len(ingredients_dict)}"

        from django.http import HttpResponse

        response = HttpResponse(
            shopping_list, content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class FavoriteListView(generics.ListAPIView):
    """Список избранного"""

    serializer_class = FavoritesSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorites.objects.select_related(
            "recipe", "recipe__author"
        ).filter(user=self.request.user)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для Ингридиентов"""

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
