"""Маршруты для АПИ выполненые с помощью роутеров"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

"""Подключение роутеров для вьюсетов"""
router.register('users', views.UserViewSet)
router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngerientViewSet)

urlpatterns = [path('', include(router.urls)),]
