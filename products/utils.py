import logging
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import WebhookLog
from decimal import Decimal

logger = logging.getLogger(__name__)


def cleanup_old_webhooks():
    try:
        cutoff = timezone.now() - timedelta(
            days=getattr(settings, "WEBHOOK_LOG_RETENTION_DAYS", 7)
        )

        deleted_count, _ = WebhookLog.objects.filter(
            created_at__lt=cutoff
        ).delete()

        logger.info(f"Cleaned {deleted_count} old webhook logs")

    except Exception:
        logger.error("Webhook cleanup failed", exc_info=True)



def safe_decimal(value, default=None):
    try:
        return Decimal(str(value)) if value else default
    except Exception:
        return default