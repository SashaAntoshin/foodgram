from django.db import models

from django.contrib.auth.models import AbstractUser, BaseUserManager

MAX_LENGTH = 200


class User(AbstractUser):
    """Модель пользователя."""
    username = models.CharField(
        max_length=MAX_LENGTH,
        blank=False,
        verbose_name='Имя пользователя',
        help_text='Обязательное поле'
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Имя',
        blank=False
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH,
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
    avatar = models.ImageField(upload_to='users/avatars', blank=True, null=True)
    groups = None
    user_permissions = None
    is_admin = models.BooleanField(
        default=False,
        verbose_name='Админ'
    )

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