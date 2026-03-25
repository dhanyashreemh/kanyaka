import requests
import os
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

SHOPIFY_CACHE_TTL = 60 * 2

def get_shopify_headers(token):
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

def update_product_price(variant_id, new_price):

    SHOP = os.getenv("SHOPIFY_STORE")
    ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

    if not SHOP or not ACCESS_TOKEN:
        return {"success": False, "error": "Server misconfiguration"}
    
    variant_id = str(variant_id).split("/")[-1]
    url = f"https://{SHOP}.myshopify.com/admin/api/2024-10/variants/{variant_id}.json"
    logger.info(f"SHOPIFY URL: {url}")

    payload = {
        "variant": {
            "id": variant_id,
            "price": new_price
        }
    }

    try:
        response = requests.put(
            url,
            json=payload,
            headers=get_shopify_headers(ACCESS_TOKEN),
            timeout=5
        )
        response.raise_for_status()

        cache.delete(f"shopify_products_{SHOP}")

        logger.info(f"Updated Shopify variant {variant_id}")

        return {"success": True, "data": response.json()}

    except requests.exceptions.Timeout:
        logger.error("Shopify update timeout")
        return {"success": False, "error": "Timeout"}

    except requests.exceptions.RequestException as e:
        logger.error("Shopify update failed", exc_info=True)
        return {"success": False, "error": str(e)}


def get_shopify_products():

    SHOP = os.getenv("SHOPIFY_STORE")
    ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

    if not SHOP or not ACCESS_TOKEN:
        return {"success": False, "error": "Server misconfiguration"}

    cache_key = f"shopify_products_{SHOP}"

    cached = cache.get(cache_key)
    if cached:
        logger.info("Returning cached Shopify products")
        return {"success": True, "data": cached}

    url = f"https://{SHOP}.myshopify.com/admin/api/2024-10/products.json?limit=50"
    logger.info(f"SHOPIFY URL: {url}")

    try:
        response = requests.get(
            url,
            headers=get_shopify_headers(ACCESS_TOKEN),
            timeout=5
        )
        response.raise_for_status()

        data = response.json() if response.content else {}

    except requests.exceptions.Timeout:
        logger.error("Shopify timeout")
        return {"success": False, "error": "Timeout"}

    except requests.exceptions.RequestException as e:
        logger.error("Shopify error", exc_info=True)
        return {"success": False, "error": str(e)}

    result = data.get("products", [])

    logger.info(f"Fetched {len(result)} Shopify products")

    cache.set(cache_key, result, SHOPIFY_CACHE_TTL)

    return {"success": True, "data": result}