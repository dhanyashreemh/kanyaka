from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .shopify_graphql import bulk_create_products


@csrf_exempt
def create_bulk_products(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            products = body.get("products", [])

            result = bulk_create_products(products)

            return JsonResponse({
                "status": "success",
                "data": result
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Only POST allowed"}, status=405)