#Create your views here.
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .shopify_graphql import create_products_sync
from .shopify_graphql import bulk_create_products
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@csrf_exempt
def create_bulk_products(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            products = body.get("products", [])

            result = create_products_sync(products)

            return JsonResponse({
                "status": "success",
                "data": result
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Only POST allowed"}, status=405)


@api_view(["POST"])
def create_bulk_products(request):
    products = request.data.get("products")

    if not products:
        return Response({"error": "No products provided"}, status=400)

    result = bulk_create_products(products)

    return Response(result)