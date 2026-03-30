from django.conf import settings
from products.models import Product
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from decimal import Decimal
import json
import hmac
import hashlib
import base64 
from products.utils import cleanup_old_webhooks
from products.models import WebhookLog
from products.services.metafields import (
    get_shopify_metafields
)
from products.utils import safe_decimal
  
def extract_image(data):
    # single image
    if data.get("image"):
        return data["image"].get("src")

    # multiple images fallback
    images = data.get("images", [])
    if images:
        return images[0].get("src")

    return None


def sync_product_images(product, data):
    from products.models import ProductImage

    images = data.get("images", [])

    if not images:
        return

    # clear old images
    ProductImage.objects.filter(product=product).delete()

    new_images = []

    for img in images:
        new_images.append(ProductImage(
            product=product,
            shopify_image_id=img.get("id"),
            image_url=img.get("src"),
            alt_text=img.get("alt")
        ))

    ProductImage.objects.bulk_create(new_images)

@csrf_exempt
def handle_shopify_webhook(request):

    if request.method != "POST":
        return HttpResponse(status=405)

    cleanup_old_webhooks()

    try:
        received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
        secret = settings.SHOPIFY_WEBHOOK_SECRET
        print("SECRET USED:", secret) 
        if not received_hmac or not secret:
            return HttpResponse(status=401)

        digest = hmac.new(
            secret.encode("utf-8"),
            request.body,
            hashlib.sha256
        ).digest()

        calculated_hmac = base64.b64encode(digest).decode()

        if not hmac.compare_digest(str(received_hmac), str(calculated_hmac)):
            return HttpResponse(status=401)

        print("✅ PRODUCT WEBHOOK VERIFIED")

        webhook_id = request.headers.get("X-Shopify-Webhook-Id")

        if not webhook_id:
            return HttpResponse(status=400)

        if WebhookLog.objects.filter(webhook_id=webhook_id).exists():
            print("⚠️ Duplicate webhook skipped")
            return HttpResponse(status=200)

        # Save webhook
        WebhookLog.objects.create(
            webhook_id=webhook_id,
            topic=request.headers.get("X-Shopify-Topic")
        )

        topic = request.headers.get("X-Shopify-Topic")
        data = json.loads(request.body)

        print("🔥 WEBHOOK:", topic)

        if topic in ["products/create", "products/update"]:

            raw_product_id = data.get("id")
            product_gid = f"gid://shopify/Product/{raw_product_id}"

            # Fetch metafields from Shopify
            metafields = get_shopify_metafields(product_gid)

            weight        = safe_decimal(metafields.get("gold_weight"))
            purity        = metafields.get("gold_purity")
            stone_type    = metafields.get("stone_type")
            cost_per_item = safe_decimal(metafields.get("making_charge"))

            for variant in data.get("variants", []):
                variant_id = variant.get("id")

                if not variant_id:
                    print("❌ Missing variant ID")
                    continue

                try:
                    obj, created = Product.objects.update_or_create(
                        shopify_variant_id=str(variant_id),  
                        defaults={
                            # IDs
                            "shopify_product_id": product_gid,

                            # Basic Info
                            "title": data.get("title"),
                            "description": data.get("body_html"),

                            # Pricing
                            "price": safe_decimal(variant.get("price"), Decimal("0")),
                            "compare_price": safe_decimal(variant.get("compare_at_price")),

                            # Classification
                            "collection": data.get("product_type"),
                            "tags": data.get("tags"),

                            # Jewelry
                            "weight": weight,
                            "purity": purity,
                            "stone_type": stone_type,
                            "cost_per_item": cost_per_item,

                            # Inventory
                            "sku": variant.get("sku"),
                            "barcode": variant.get("barcode"),
                            "quantity": variant.get("inventory_quantity") or 0,

                            "inventory_tracked": variant.get("inventory_management") == "shopify",
                            "sell_out_of_stock": variant.get("inventory_policy") == "continue",
                            "charge_tax": variant.get("taxable", True),

                            "image_url": extract_image(data),
                            "raw_data": data,
                        }
                    )

                    sync_product_images(obj, data)

                    print(f"✅ Synced variant {variant_id}")

                except Exception as e:
                    print(f"❌ Error saving variant {variant_id}: {str(e)}")

        elif topic == "products/delete":
          print("⚠️ Delete webhook received")

          product_id = data.get("id")
          product_gid = f"gid://shopify/Product/{product_id}"

          deleted_count, _ = Product.objects.filter(
              shopify_product_id=product_gid
          ).delete()

          print(f"🗑️ Deleted {deleted_count} records")

        return HttpResponse(status=200)

    except Exception as e:
        print("❌ WEBHOOK ERROR:", str(e))
        return HttpResponse(status=500)
    

