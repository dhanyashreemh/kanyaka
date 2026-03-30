from django.conf import settings
from .shopify_base import shopify_request
from .metafields import get_shopify_metafields
import requests
from products.models import Product
from products.utils import safe_decimal
from decimal import Decimal
import logging
from django.db.models.signals import post_save
from business.signals import trigger_single_product_update

logger = logging.getLogger(__name__)

def find_variant_by_sku(sku):
    query = f"""
    {{
      productVariants(first: 1, query: "sku:{sku}") {{
        edges {{
          node {{
            id
            product {{ id }}
          }}
        }}
      }}
    }}
    """

    data = shopify_request(query)


    if not data.get("data"):
        return None

    edges = data["data"]["productVariants"]["edges"]

    if edges:
        return edges[0]["node"]

    return None


def create_product(product):

    # Step 1: Create product
    mutation = f"""
    mutation {{
      productCreate(product: {{
        title: "{product['title']}",
        status: ACTIVE
      }}) {{
        product {{
          id
          variants(first: 1) {{
            edges {{
              node {{
                id
                inventoryItem {{ id }}
              }}
            }}
          }}
        }}
        userErrors {{ message }}
      }}
    }}
    """

    data = shopify_request(mutation)

    if data.get("errors"):
        return data

    product_data = data["data"]["productCreate"]["product"]
    variant_node = product_data["variants"]["edges"][0]["node"]

    product_id = product_data["id"]
    variant_id = variant_node["id"]
    inventory_item_id = variant_node["inventoryItem"]["id"]

    # Step 2: Update variant price + sku
    update_variant = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{product_id}",
        variants: [{{
          id: "{variant_id}",
          price: "{product['price']}",
          sku: "{product['sku']}"
        }}]
      ) {{
        userErrors {{ message }}
      }}
    }}
    """

    shopify_request(update_variant)

    return data

def update_product(existing_variant, product):

    mutation = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{existing_variant['product']['id']}",
        variants: [{{
          id: "{existing_variant['id']}",
          price: "{product['price']}"
        }}]
      ) {{
        userErrors {{ message }}
      }}
    }}
    """

    return shopify_request(mutation)

def sync_products(products):
    results = {"created": 0, "updated": 0, "errors": []}

    for product in products:
        existing = find_variant_by_sku(product["sku"])

        if existing:
            response = update_product(existing, product)
            results["updated"] += 1
        else:
            response = create_product(product)
            results["created"] += 1
 
        errors = response.get("data", {}).get("productCreate", {}).get("userErrors", [])
        if errors:
            results["errors"].append(errors)

    return results


def sync_products_service():

    # 🔥 DISABLE PRODUCT SIGNAL (CRITICAL FIX)
    post_save.disconnect(trigger_single_product_update, sender=Product)

    try:
        url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/products.json?limit=250"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        while url:
            response = requests.get(url, headers=headers)
            data = response.json()

            print("PRODUCT COUNT:", len(data.get("products", [])))

            for product in data.get("products", []):

                product_gid = f"gid://shopify/Product/{product['id']}"

                # 🔥 Fetch metafields
                metafields = get_shopify_metafields(product_gid)

                weight        = safe_decimal(metafields.get("gold_weight"))
                purity        = metafields.get("gold_purity")
                stone_type    = metafields.get("stone_type")
                cost_per_item = safe_decimal(metafields.get("making_charge"))

                for variant in product.get("variants", []):

                    Product.objects.update_or_create(
                        shopify_variant_id=str(variant["id"]),   # 🔥 always string
                        defaults={
                            # IDs
                            "shopify_product_id": product_gid,

                            # Basic Info
                            "title":       product.get("title"),
                            "description": product.get("body_html"),

                            # Pricing
                            "price":         safe_decimal(variant.get("price"), Decimal("0")),
                            "compare_price": safe_decimal(variant.get("compare_at_price")),

                            # Classification
                            "collection": product.get("product_type") or "General",
                            "tags":       product.get("tags"),

                            # Jewelry
                            "weight":        weight,
                            "purity":        purity,
                            "stone_type":    stone_type,
                            "cost_per_item": cost_per_item,

                            # Inventory
                            "sku":     variant.get("sku"),
                            "barcode": variant.get("barcode"),
                            "quantity": variant.get("inventory_quantity", 0),

                            "inventory_tracked": variant.get("inventory_management") == "shopify",
                            "sell_out_of_stock": variant.get("inventory_policy") == "continue",
                            "charge_tax":        variant.get("taxable", True),

                            # Raw backup
                            "raw_data": product,
                        }
                    )

                    logger.info(f"✅ Synced: {product['title']}")

            # 🔁 Pagination handling
            link_header = response.headers.get("Link")
            if link_header and 'rel="next"' in link_header:
                url = link_header.split(";")[0].strip("<> ")
            else:
                url = None

        logger.info("🎉 Sync completed successfully")

    finally:
        # 🔥 RE-ENABLE SIGNAL (VERY IMPORTANT)
        post_save.connect(trigger_single_product_update, sender=Product)