from email.message import EmailMessage
from smtplib import SMTP

from core.config.config import settings


def send_magic_link_email(to_email: str, magic_link: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Seu link de acesso ao Homely"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        "Use o link abaixo para entrar no Homely. Ele expira em "
        f"{settings.MAGIC_LINK_EXPIRE_MINUTES} minutos.\n\n{magic_link}\n"
    )

    with SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.send_message(message)
