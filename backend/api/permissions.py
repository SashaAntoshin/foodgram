"""Кастомные права для разных пользователей"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Права для администратора."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_admin
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Права на создание и редактирование только для админа"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return IsAdmin().has_permission(request, view)


class IsAuthorOrIsAdmin(permissions.BasePermission):
    """Права для автора и админа"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_admin
