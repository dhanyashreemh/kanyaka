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
  
@csrf_exempt
def handle_shopify_webhook(request):
    # 🧹 cleanup old webhook logs
    cleanup_old_webhooks()
    try:
        received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
        secret = settings.SHOPIFY_WEBHOOK_SECRET

        calculated_hmac = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                request.body,
                hashlib.sha256
            ).digest()
        ).decode()

        if not received_hmac or not hmac.compare_digest(received_hmac, calculated_hmac):
            print("❌ HMAC verification failed")
            return HttpResponse(status=401)

        print("✅ PRODUCT WEBHOOK VERIFIED")


        webhook_id = request.headers.get("X-Shopify-Webhook-Id")

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
                    Product.objects.update_or_create(
                        shopify_variant_id=variant_id,
                        defaults={
                            # IDs
                            "shopify_product_id": product_gid,

                            # Basic Info
                            "title":       data.get("title"),
                            "description": data.get("body_html"),

                            # Pricing
                            "price":         safe_decimal(variant.get("price"), Decimal("0")),
                            "compare_price": safe_decimal(variant.get("compare_at_price")),

                            # Classification
                            "collection": data.get("product_type"),
                            "tags":       data.get("tags"),

                            # Jewelry (from metafields)
                            "weight":        weight,
                            "purity":        purity,
                            "stone_type":    stone_type,
                            "cost_per_item": cost_per_item,

                            # ❌ jewelry_type, metal_type, occasion → Django master, never touch here

                            # Inventory
                            "sku":      variant.get("sku"),
                            "barcode":  variant.get("barcode"),
                            "quantity": variant.get("inventory_quantity") or 0,

                            "inventory_tracked":  variant.get("inventory_management") == "shopify",
                            "sell_out_of_stock":  variant.get("inventory_policy") == "continue",
                            "charge_tax":         variant.get("taxable", True),

                            # Raw backup
                            "raw_data": data,
                        }
                    )
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