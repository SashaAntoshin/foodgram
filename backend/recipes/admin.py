"""Регистрацияя моделей из приложения рецептов"""
from django.db.models import Count
from django.contrib import admin
from admin_auto_filters.filters import AutocompleteFilter

from .models import (
    Favorite,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingBasket,
    Tag,
)


class AutoFilter(AutocompleteFilter):
    title = "Автор"
    field_name = 'author'


class TagFilter(AutocompleteFilter):
    title = 'Теги'
    field_name = "tags"


class UserFilter(AutocompleteFilter):
    title = "Пользователь"
    field_name = "user"


class RecipeFilter(AutocompleteFilter):
    title = "Рецепт"
    field_name = "recipe"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "author")
    search_fields = ("name",)
    list_filter = (AutoFilter, TagFilter)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("author")
            .prefetch_related("tags", "ingredients_amounts__ingredient")
            .annotate(favorites_count=(Count("saved")))
        )

    def favorites_count(self, obj):
        """Количество добавлений в избранное."""
        return obj.favorites_count

    favorites_count.short_description = "В избранном"
    favorites_count.admin_order_field = "favorites_count"


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)


@admin.register(IngredientsInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "amount")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("recipe", "ingredient")
        )


@admin.register(ShoppingBasket)
class ShoppingBasketAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "added_at")
    list_filter = (UserFilter, RecipeFilter)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "recipe")
        )


@admin.register(Favorite)
class FavoritesAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "added_at")
    list_filter = (UserFilter, RecipeFilter)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "recipe")
        )
