"""Notification service — in-app and email notifications."""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.core.config import settings

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, type: str, title: str, body: str | None = None, data: dict | None = None) -> Notification:
        notif = Notification(user_id=user_id, type=type, title=title, body=body, data=data)
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send email via configured provider. Falls back to console logging in dev."""
        provider = settings.EMAIL_PROVIDER

        if provider == "console":
            logger.info(
                "EMAIL (console adapter — not actually sent)",
                to=to,
                subject=subject,
                body_preview=body[:200],
            )
            return

        if provider == "smtp":
            import smtplib
            from email.mime.text import MIMEText
            try:
                msg = MIMEText(body, "html")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_FROM
                msg["To"] = to
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        smtp.starttls()
                        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    smtp.send_message(msg)
                logger.info("Email sent", to=to, subject=subject)
            except Exception as e:
                logger.error("Email send failed", to=to, subject=subject, error=str(e))
                raise
        else:
            logger.warning("Unknown email provider", provider=provider)
