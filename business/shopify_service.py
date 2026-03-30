import requests
import os
from django.core.cache import cache
import logging
from django.conf import settings

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
    
    # gid://shopify/ProductVariant/12345 → 12345
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

def sync_images_to_shopify(product):

    # 🔥 STEP 1: DELETE OLD IMAGES
    delete_all_shopify_images(product)

    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    media = []

    # ✅ SINGLE IMAGE SUPPORT
    if product.image_url:
        media.append({
            "originalSource": product.image_url,
            "mediaContentType": "IMAGE"
        })

    if not media:
        print("⚠️ No images to sync")
        return

    mutation = """
    mutation addMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          ... on MediaImage {
            id
            image {
              url
            }
          }
        }
        mediaUserErrors { message }
      }
    }
    """

    variables = {
        "productId": product.shopify_product_id,
        "media": media
    }

    res = requests.post(
        url,
        json={"query": mutation, "variables": variables},
        headers=headers
    ).json()

    print("🟢 IMAGE SYNC:", res)

def delete_all_shopify_images(product):

    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    # get media ids
    query = """
    query getProductMedia($id: ID!) {
      product(id: $id) {
        media(first: 20) {
          edges {
            node {
              id
            }
          }
        }
      }
    }
    """

    res = requests.post(url, json={"query": query, "variables": {"id": product.shopify_product_id}}, headers=headers).json()

    media_edges = res.get("data", {}).get("product", {}).get("media", {}).get("edges", [])
    media_ids = [edge["node"]["id"] for edge in media_edges]

    if not media_ids:
        print("⚠️ No images to delete")
        return

    mutation = """
    mutation deleteMedia($ids: [ID!]!) {
      productDeleteMedia(mediaIds: $ids) {
        deletedMediaIds
        userErrors { message }
      }
    }
    """

    res2 = requests.post(
        url,
        json={"query": mutation, "variables": {"ids": media_ids}},
        headers=headers
    ).json()

    print("🗑️ Deleted Images:", res2)


