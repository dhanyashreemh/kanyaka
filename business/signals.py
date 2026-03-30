import logging
import time
from threading import Thread
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import GoldRate
from products.models import Product
from .services import update_single_product
from .services import update_all_products

logger = logging.getLogger(__name__)

LOCK_KEY = "price_update_lock"
LOCK_TIMEOUT = 600  # 10 mins
LAST_RUN_KEY = "last_gold_update_time"


def run_in_thread(rate):
    if cache.get(LOCK_KEY):
        logger.warning("⚠️ Price update already running, skipping")
        return

    cache.set(LOCK_KEY, True, timeout=LOCK_TIMEOUT)

    try:
        logger.info("🚀 Starting async product update...")
        update_all_products(rate)
        logger.info("✅ Product update completed")
    except Exception:
        logger.error("❌ Product update failed", exc_info=True)
    finally:
        cache.delete(LOCK_KEY)


@receiver(post_save, sender=GoldRate)
def trigger_price_update(sender, instance, created, **kwargs):

    # 🔥 prevent too frequent updates
    now = time.time()
    last = cache.get(LAST_RUN_KEY)

    if last and now - last < 60:
        logger.warning("⚠️ Skipping frequent gold updates")
        return

    cache.set(LAST_RUN_KEY, now, timeout=60)

    # 🔥 prevent duplicate threads
    if cache.get(LOCK_KEY):
        logger.warning("⚠️ Update already running, skipping trigger")
        return

    logger.info(f"💰 GoldRate changed (created={created}) → triggering async update")

    cache.delete("gold_rate:latest")

    Thread(
        target=run_in_thread,
        args=(instance,),
        daemon=True
    ).start()




def run_single_update(product):
    try:
        update_single_product(product)
        logger.info(f"✅ Single product updated: {product.title}")
    except Exception:
        logger.error("❌ Single product update failed", exc_info=True)


@receiver(post_save, sender=Product)
def trigger_single_product_update(sender, instance, created, **kwargs):

    # 🔥 SKIP during Shopify sync (NEW FIX)
    if getattr(instance, "_skip_shopify", False):
        return

    # 🔥 PREVENT INFINITE LOOP (already exists)
    if getattr(instance, "_updating_price", False):
        return

    logger.info(f"🛠 Product changed → updating {instance.title}")

    Thread(
        target=run_single_update,
        args=(instance,),
        daemon=True
    ).start()