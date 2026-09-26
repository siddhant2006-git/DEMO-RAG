from email.message import EmailMessage
import smtplib

from app.config import get_settings


class EmailDeliveryError(Exception):
    pass


def send_auth_email(*, recipient: str, subject: str, link: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise EmailDeliveryError("SMTP is not configured")
    try:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(f"Use this secure link to continue: {link}")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, ValueError, UnicodeError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Authentication email could not be delivered") from exc
