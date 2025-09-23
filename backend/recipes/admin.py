"""Регистрацияя моделей из приложения рецептов"""
from django.contrib import admin

from .models import (
    Tag,
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    Favorites,
    ShoppingBasket
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    filter_horizontal = ('tags',)
    

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit')
    search_fields = ('name',)
    

@admin.register(IngredientsInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(ShoppingBasket)
class ShoppingBasketAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'recipe__name')


@admin.register(Favorites)
class FavoritesAdmin(admin.ModelAdmin):
    list_display = ('favorite_cook', 'recipe', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('favorite_cook__username', 'recipe__name')