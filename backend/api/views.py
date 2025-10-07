from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.paginations import CustomPagination
from api.serializers import (
    AvatarUpdateSerializer,
    FavoritesSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    SubscriptionSerializer,
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

from users.models import Follow

from .filters import RecipeFilter
from .paginations import CustomPagination
from .permissions import IsAuthorOrIsAdmin, IsAuthorOrReadOnly
from .serializers import (
    UserListSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


User = get_user_model()

class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов"""

    permission_classes = [IsAuthorOrIsAdmin, IsAuthorOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "tags", "ingredients_amounts__ingredient"
        )

        is_favorited = self.request.query_params.get("is_favorited")
        if is_favorited == "1" and self.request.user.is_authenticated:
            favorite_ids = Favorite.objects.filter(
                user=self.request.user
            ).values_list("recipe_id", flat=True)
            queryset = queryset.filter(id__in=favorite_ids)

        is_in_cart = self.request.query_params.get("is_in_shopping_cart")
        if is_in_cart == "1" and self.request.user.is_authenticated:
            cart_ids = ShoppingBasket.objects.filter(
                user=self.request.user
            ).values_list("recipe_id", flat=True)
            queryset = queryset.filter(id__in=cart_ids)

        return queryset.distinct()

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

        deleted_favorite, _ = Favorite.objects.filter(
            user=user, recipe=recipe
        ).delete()

        if deleted_favorite == 0:
            return Response(
                {"detail": "Рецепт не найден в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            # коллекция прошла, наверное опять я
            # не понял твоего замечания, Роман)
            deleted_count, _ = ShoppingBasket.objects.filter(
                user=user, recipe=recipe
            ).delete()

            if deleted_count == 0:
                return Response(
                    {"detail": "Рецепт не найден в корзине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    def _generate_shopping_list_content(self, user):
        """Генерация содержимого списка покупок"""
        ingredients = (
            IngredientsInRecipe.objects.filter(
                recipe__in_shopping_basket__user=user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        shopping_list = "Список покупок:\n\n"
        for ing in ingredients:
            name = ing["ingredient__name"]
            amount = ing["total_amount"]
            unit = ing["ingredient__measurement_unit"]
            shopping_list += f"- {name} - {amount} {unit}\n"
        shopping_list += f"\nВсего ингредиентов: {len(ingredients)}"

        return shopping_list

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок с оптимизацией запросов."""
        user = request.user
        shopping_list_content = self._generate_shopping_list_content(user)

        response = HttpResponse(
            shopping_list_content, content_type="text/plain; charset=utf-8"
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


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для Юзера"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        return UserListSerializer

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Подписка/отписка на автора."""
        author = self.get_object()
        user = request.user

        if request.method == "POST":
            follow_serializer = FollowSerializer(
                data={"author": author.id}, context={"request": request}
            )
            follow_serializer.is_valid(raise_exception=True)
            follow_serializer.save(user=user)
            serializer = SubscriptionSerializer(
                author,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            deleted_count, _ = Follow.objects.filter(
                user=user, author=author
            ).delete()

            if deleted_count == 0:
                return Response(
                    {"detail": "Подписка не найдена"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Список моих подписок."""
        user = request.user
        subscribed_authors = (
            User.objects.filter(following__user=user)
            .prefetch_related("recipes")
            .annotate(recipes_count=Count("recipes"))
        )
        page = self.paginate_queryset(subscribed_authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class UserListView(APIView):
    """Отдельный вью только для списка пользователей."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = User.objects.all()
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class MeView(APIView):
    """Вью для user/me."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserListSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)


class UserAvatarView(APIView):
    """Вью для аватара."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self, request):
        """Обновление."""
        serializer = AvatarUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        """Удаление."""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePassword(APIView):
    """Смена пароля."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not user.check_password(current_password):
            return Response(
                {"detail": "Неверный текущий пароль"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowViewSet(viewsets.ModelViewSet):
    """Вьюсет модели подписок."""

    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Отключаем базовый POST /follows/ в пользу action subscribe."""
        return Response(
            {"detail": "Используйте POST /follows/subscribe/{author_id}/"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"])
    def subscriptions(self, request):
        """Подписки пользователя."""
        follows = self.get_queryset()
        serializer = self.get_serializer(follows, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"])
    def subscribe(self, request, pk=None):
        """Подписаться / Отписаться."""
        author = get_object_or_404(User, pk=pk)

        if request.method == "POST":
            serializer = self.get_serializer(data={"author": author.id})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == "DELETE":
            follow = get_object_or_404(
                Follow, user=request.user, author=author
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListView(generics.ListAPIView):
    """Список избранного."""

    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.select_related(
            "recipe", "recipe__author"
        ).filter(user=self.request.user)
