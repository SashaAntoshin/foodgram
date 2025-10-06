import django_filters
from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    """Кастомная фильтрация рецептов"""

    author = django_filters.NumberFilter(field_name="author__id")
    tags = django_filters.AllValuesMultipleFilter(field_name="tags__slug")
    is_favorite = django_filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = django_filters.BooleanFilter(
		method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ["author", "tags",]

    def filter_is_favorited(self, queryset, name, value):
        user = getattr(self.request, 'user', None)
        if user and value and not user.is_anonymous:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = getattr(self.request, 'user', None)
        if user and value and not user.is_anonymous:
            return queryset.filter(shoppingcart__user=user)
        return queryset
