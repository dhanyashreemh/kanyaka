# business/utils.py

import time
from decimal import Decimal
from products.models import Product
from .shopify_service import update_product_price
from .views import calculate_price   # or move this also to utils

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

            product.price = new_price
            product.save(update_fields=["price"])

            if product.shopify_variant_id:
                update_product_price(product.shopify_variant_id, float(new_price))
                time.sleep(0.3)

            print(f"✅ {product.title} → ₹{new_price}")

        except Exception as e:
            print(f"❌ {product.title}: {e}")