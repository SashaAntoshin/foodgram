"""Маршруты для АПИ выполненые с помощью роутеров"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from users.views import FollowViewSet, UserViewSet

router = DefaultRouter()

"""Подключение роутеров для вьюсетов"""
router.register('users', UserViewSet)
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngerientViewSet)
router.register('follow', FollowViewSet, basename='follow')

urlpatterns = [path('', include(router.urls)),]
