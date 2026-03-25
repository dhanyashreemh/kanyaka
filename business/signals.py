import logging
from threading import Thread
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import GoldRate
from .services import update_all_products

logger = logging.getLogger(__name__)


def run_in_thread(rate):

    lock_key = "price_update_lock"

    if cache.get(lock_key):
        logger.warning("⚠️ Price update already running, skipping")
        return

    cache.set(lock_key, True, timeout=60)

    try:
        update_all_products(rate)
    except Exception:
        logger.error("Product update failed", exc_info=True)
    finally:
        cache.delete(lock_key)


@receiver(post_save, sender=GoldRate)
def trigger_price_update(sender, instance, created, **kwargs):

    logger.info(f"GoldRate saved (created={created}) → updating all products")

    # 🧹 clear cache
    cache.delete("gold_rate:latest")

    Thread(
        target=run_in_thread,
        args=(instance,),
        daemon=True
    ).start()