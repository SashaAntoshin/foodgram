from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

MAX_LENGTH = 150


class User(AbstractUser):
    """Модель пользователя."""

    username = models.CharField(
        max_length=MAX_LENGTH,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
                message='Разрешены только буквы, цифры и символы @/./+/-/_'
            )
        ],
        verbose_name="Имя пользователя",
        help_text="Обязательное поле",
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Имя")
    last_name = models.CharField(
        max_length=MAX_LENGTH,
        blank=False,
        verbose_name="Фамилия",
        help_text="Обязательное поле",
    )
    bio = models.TextField(blank=True, verbose_name="Об авторе")
    email = models.EmailField(
        max_length=256, unique=True, help_text="Обязательное поле")
    avatar = models.ImageField(
        upload_to="users/avatars", blank=True, null=True, verbose_name="аватар"
    )
    groups = None
    user_permissions = None
    is_admin = models.BooleanField(default=False, verbose_name="Админ")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "last_name"]

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.username}"


class Follow(models.Model):
    """Модель подписок"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="подписчик",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="автор",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="дата подписки"
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_follow"
            )
        ]

    def __str__(self):
        return f"{self.user} подписан на {self.author}"
