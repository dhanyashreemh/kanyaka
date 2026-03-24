# business/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from threading import Thread

from .models import GoldRate
from .utils import update_all_products   # 👈 import from ONE place


@receiver(post_save, sender=GoldRate)
def trigger_price_update(sender, instance, created, **kwargs):
    print("🔥 GoldRate saved → updating all products")

    # 🚀 run in background
    Thread(target=update_all_products, args=(instance,)).start()