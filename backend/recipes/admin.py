"""Регистрацияя моделей из приложения рецептов"""

from django.contrib import admin
from django.db.models import Count

from .models import (
    Favorite,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    ShoppingBasket,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "author")
    search_fields = ("name", "author__username")
    list_filter = ("tags",)
    filter_horizontal = ("tags",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            favorites_count=Count("favorites")
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


@admin.register(ShoppingBasket)
class ShoppingBasketAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "recipe__name")


@admin.register(Favorite)
class FavoritesAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "recipe__name")
