"""Регистрацияя моделей из приложения рецептов"""
from django.contrib import admin

from .models import Tag, Recipe, Ingredient, IngredientsInRecipe


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