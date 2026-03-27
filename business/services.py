from django.core.cache import cache
from .models import GoldRate
import logging
from products.models import Product
from .shopify_service import update_product_price
from .pricing import calculate_price 
from products.services.metafields import update_product_metafields 
from concurrent.futures import ThreadPoolExecutor


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



def process_product(product, rate_obj):
    try:
        if not product.weight:
            return

        new_price = calculate_price(
            weight=product.weight,
            rate22=rate_obj.rate_22k,
            making=rate_obj.making_charge_per_gram,
            gst=rate_obj.gst_percentage,
            making_type=rate_obj.making_type,
            stone=product.cost_per_item
        )

        # ✅ Skip if no change
        if product.price == new_price:
            return

        # 🔥 Prevent signal loop
        product._updating_price = True

        # ✅ Update DB
        product.price = new_price
        product.save(update_fields=["price"])

        # ✅ Shopify update (only if needed)
        if product.shopify_variant_id:
            update_product_price(product.shopify_variant_id, float(new_price))

        if product.shopify_product_id:
            update_product_metafields(product)

        logger.info(f"✅ {product.title} → ₹{new_price}")

    except Exception as e:
        logger.error(f"❌ {product.title}: {e}", exc_info=True)


def update_all_products(rate_obj):
    product_ids = Product.objects.exclude(weight__isnull=True)\
                                 .values_list("id", flat=True)

    total = len(product_ids)
    logger.info(f"📦 Updating {total} products...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(lambda pid: process_product_by_id(pid, rate_obj), product_ids)

    logger.info("🎉 All products updated successfully")

    logger.info("🎉 All products updated successfully")

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

def update_single_product(product):

    from .models import GoldRate

    gold_rate = GoldRate.objects.latest("created_at")

    new_price = calculate_price(
        weight=product.weight,
        rate22=gold_rate.rate_22k,
        making=gold_rate.making_charge_per_gram,
        gst=gold_rate.gst_percentage,
        making_type=gold_rate.making_type,
        stone=product.cost_per_item
    )

    if product.price == new_price:
        return

    # 🔥 THIS LINE IS CRITICAL
    product._updating_price = True

    product.price = new_price
    product.save(update_fields=["price"])

    if product.shopify_variant_id:
        update_product_price(product.shopify_variant_id, float(new_price))

    if product.shopify_product_id:
        update_product_metafields(product)

def process_product_by_id(product_id, rate_obj):
    from products.models import Product

    try:
        product = Product.objects.get(id=product_id)
        process_product(product, rate_obj)

    except Exception as e:
        logger.error(f"❌ Product ID {product_id}: {e}", exc_info=True)