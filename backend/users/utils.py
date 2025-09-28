from django.core.mail import send_mail


def send_confirmation_code(user):
    """Отправка кода подтверждения при ригистрации"""
    send_mail(
        subject="Код подтверждения",
        message=f"Ваш код {user.get_confirmation_code()}",
        from_email=None,
        recipient_list=[user.email],
    )
