from django.utils import timezone
from datetime import timedelta
from .models import WebhookLog
from .models import WebhookLog

def cleanup_old_webhooks():
    deleted_count, _ = WebhookLog.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=7)
    ).delete()

    print(f"Cleaned {deleted_count} old webhook logs")