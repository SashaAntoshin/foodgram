"""Маршруты для АПИ выполненые с помощью роутеров"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from users.views import FollowViewSet, UserViewSet, MeView, UserAvatarView, ChangePassword, LogoutView

router = DefaultRouter()

"""Подключение роутеров для вьюсетов"""
router.register('users', UserViewSet, basename='user')
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet, basename='tag')
router.register('ingredients', views.IngredientViewSet, basename='ingredients')
router.register('follow', FollowViewSet, basename='follow')

urlpatterns = [
	path('users/me/', MeView.as_view(), name='user-me'),
	path('users/me/avatar/', UserAvatarView.as_view(), name='user-avatar'),
	path('users/set_password/', ChangePassword.as_view(), name='set-password'),
    path('', include(router.urls)),
    path('favorites/', views.FavoriteListView.as_view(), name='favorite-list'),
	path('api/auth/token/logout/', LogoutView.as_view(), name='logout'),
]
