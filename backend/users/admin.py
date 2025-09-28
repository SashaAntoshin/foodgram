from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomRegistratonForm(forms.ModelForm):
    """Форма создания пользователя через админку"""

    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "password")


@admin.register(User)
class NewUserAdmin(UserAdmin):
    """Кастомная админка пользователя"""

    add_form = CustomRegistratonForm
    add_fieldsets = (
        (
            "Основная информация",
            {
                "classes": ("wide",),
                "fields": ("email", "username", "first_name", "last_name"),
            },
        ),
    )
    search_fields = ("email", "username")
    list_filter = ("is_staff", "is_active")
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "username")
    filter_horizontal = []
    fieldsets = (
        ("Основная информация", {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
