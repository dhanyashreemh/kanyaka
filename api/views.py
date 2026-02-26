import requests
import os
from dotenv import load_dotenv

from rest_framework.decorators import api_view
from rest_framework.response import Response

# load_dotenv()

# @api_view(['GET'])
# def test_api(request):
#     SHOP = os.getenv("SHOPIFY_STORE")
#     ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

#     url = f"https://{SHOP}.myshopify.com/admin/api/2026-01/products.json"

#     headers = {
#         "X-Shopify-Access-Token": ACCESS_TOKEN,
#         "Content-Type": "application/json"
#     }

#     response = requests.get(url, headers=headers)

#     return Response({
#         "status_code": response.status_code,
#         "response": response.json() if response.status_code == 200 else response.text
#     })

@api_view(['GET'])
def test_api(request):
    SHOP = os.getenv("SHOPIFY_STORE")
    ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

    url = f"https://{SHOP}.myshopify.com/admin/api/2026-01/products.json"

    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    if response.status_code != 200:
        return Response({
            "status_code": response.status_code,
            "error": data
        })

    cleaned_products = []

    for product in data.get("products", []):
        variant = product.get("variants", [{}])[0]
        image = product.get("image")

        cleaned_products.append({
            "id": product.get("id"),
            "title": product.get("title"),
            "price": variant.get("price"),
            "inventory": variant.get("inventory_quantity"),
            "image": image.get("src") if image else None
        })

    return Response({
        "status_code": 200,
        "products": cleaned_products
    })
