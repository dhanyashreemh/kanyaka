import requests
import os

SHOP = os.getenv("SHOPIFY_STORE")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def get_shopify_products():

    url = f"https://{SHOP}.myshopify.com/admin/api/2026-01/products.json"

    res = requests.get(url, headers=headers)

    return res.json()["products"]


def update_product_price(variant_id, new_price):

    url = f"https://{SHOP}.myshopify.com/admin/api/2026-01/variants/{variant_id}.json"

    payload = {
        "variant": {
            "id": variant_id,
            "price": new_price
        }
    }

    requests.put(url, json=payload, headers=headers)