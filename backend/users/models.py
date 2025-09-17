from django.db import models

from django.contrib.auth.models import AbstractUser, BaseUserManager

MAX_TITLE_LENGTH = 200


class User(AbstractUser):
    """Модель пользователя."""
    username = models.CharField(
        max_length=MAX_TITLE_LENGTH,
        blank=False,
        verbose_name='Имя',
        help_text='Обязательное поле'
    )
    last_name = models.CharField(
        max_length=MAX_TITLE_LENGTH,
        blank=False,
        verbose_name='Фамилия',
        help_text='Обязательное поле'

    )
    bio = models.TextField(blank=True, verbose_name='Об авторе')
    email = models.EmailField(
        max_length=256,
        unique=True,
        help_text='Обязательное поле',
        blank=False
    )
    groups = None
    user_permissions = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'last_name']

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs) 

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
       return f'{self.username}'