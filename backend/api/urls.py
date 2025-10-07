"""Маршруты для АПИ выполненые с помощью роутеров"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .views import (ChangePassword, FavoriteListView, FollowViewSet,
                         MeView, UserAvatarView, UserListView, UserViewSet)

router = DefaultRouter()

"""Подключение роутеров для вьюсетов"""
router.register("users", UserViewSet, basename="user")
router.register("recipes", views.RecipeViewSet, basename="recipes")
router.register("tags", views.TagViewSet, basename="tag")
router.register("ingredients", views.IngredientViewSet, basename="ingredients")
router.register("follow", FollowViewSet, basename="follow")

urlpatterns = [
    path("users/me/", MeView.as_view(), name="user-me"),
    path("users/me/avatar/", UserAvatarView.as_view(), name="user-avatar"),
    path("users/set_password/", ChangePassword.as_view(), name="set-password"),
    path("", include(router.urls)),
    path("favorites/", FavoriteListView.as_view(), name="favorite-list"),
    path("users-list/", UserListView.as_view()),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
]
