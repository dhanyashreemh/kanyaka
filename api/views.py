from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from business.models import GoldRate
import requests
import os


@api_view(['GET'])
def gold_rate_api(request):
    rate = GoldRate.objects.order_by('-updated_at').first()

    if not rate:
        return Response({"error": "No rate available"}, status=404)

    return Response({
        "rate_24k": str(rate.rate_24k),
        "rate_22k": str(rate.rate_22k),
    })


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

    return Response({
        "status_code": 200,
        "products": data.get("products", [])
    })