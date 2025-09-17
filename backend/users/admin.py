from django.contrib.auth.admin import UserAdmin
from django.contrib import admin

from .models import User


@admin.register(User)
class NewUserAdmin(UserAdmin):
	"""Кастомная админка пользователя"""
	list_display = ('username', 'last_name', 'email', 'is_staff')
	search_fields = ('username', 'email')
	list_filter = ('is_staff',)
	ordering = ('username',)
	filter_horizontal = ()