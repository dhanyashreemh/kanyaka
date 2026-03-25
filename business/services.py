from django.core.cache import cache
from .models import GoldRate
import logging
import time
from products.models import Product
from .shopify_service import update_product_price
from .pricing import calculate_price 
from products.services.metafields import update_product_metafields 

logger = logging.getLogger(__name__)

CACHE_KEY = "gold_rate:latest"
CACHE_TTL = 60 * 5

def get_gold_rate():

    cached_data = cache.get(CACHE_KEY)
    if cached_data:
        logger.info("Returning cached gold rate")
        return cached_data

    try:
        rate = GoldRate.objects.latest('updated_at')
    except GoldRate.DoesNotExist:
        logger.warning("No gold rate found in DB")
        return None

    data = {
        "rate_24k": str(rate.rate_24k),
        "rate_22k": str(rate.rate_22k),
        "making_charge": str(rate.making_charge_per_gram),
        "gst": str(rate.gst_percentage),
        "updated_at": rate.updated_at.isoformat()
    }

    cache.set(CACHE_KEY, data, CACHE_TTL)

    logger.info("Gold rate fetched from DB and cached")

    return data

def update_all_products(rate_obj):

    products = Product.objects.exclude(weight__isnull=True)

    for product in products:
        try:
            if not product.weight:
                continue

            new_price = calculate_price(
                weight=product.weight,
                rate22=rate_obj.rate_22k,
                making=rate_obj.making_charge_per_gram,
                gst=rate_obj.gst_percentage,
                making_type=rate_obj.making_type,
                stone=product.cost_per_item
            )

            # ✅ Only update if changed
            if product.price == new_price:
                continue

            product.price = new_price
            product.save(update_fields=["price"])

            # ✅ Shopify price update
            if product.shopify_variant_id:
                update_product_price(product.shopify_variant_id, float(new_price))

            # 🔥 ADD THIS (THIS WAS MISSING)
            if product.shopify_product_id:
                update_product_metafields(product)

            time.sleep(0.3)

            logger.info(f"✅ {product.title} → ₹{new_price}")

        except Exception as e:
            logger.error(f"{product.title}: {e}")

def create_gold_rate(data):
    try:
        return GoldRate.objects.create(
            rate_24k=data["rate_24k"],
            rate_22k=data["rate_22k"],
            making_charge_per_gram=data["making"],
            gst_percentage=data["gst"],
            making_type=data["making_type"]
        )
    except Exception:
        logger.error("GoldRate creation failed", exc_info=True)
        raise  