import json
import hmac
import hashlib
import base64
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Order


@csrf_exempt
def shopify_webhook(request):
    print("\n===== SHOPIFY WEBHOOK HIT =====")

    if request.method != "POST":
        print("Invalid method:", request.method)
        return HttpResponse(status=405)

    received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
    secret = settings.SHOPIFY_WEBHOOK_SECRET  

    if not received_hmac or not secret:
        print("Missing HMAC or secret")
        return HttpResponse(status=401)

    try:
        digest = hmac.new(
            secret.encode("utf-8"),
            request.body,
            hashlib.sha256
        ).digest()

        calculated_hmac = base64.b64encode(digest).decode()

        print("Calculated HMAC:", calculated_hmac)

        if not hmac.compare_digest(str(received_hmac), str(calculated_hmac)):
            print("HMAC verification failed")
            return HttpResponse(status=401)

    except Exception as e:
        print("HMAC ERROR:", str(e))
        return HttpResponse(status=401)

    print("HMAC verified successfully")

    try:
        order_data = json.loads(request.body)
        print("Order Payload Received")

        order_id = order_data.get("id")
        if not order_id:
            print("No Order ID in payload")
            return HttpResponse(status=400)

        print("Order ID:", order_id)

        order, created = Order.objects.get_or_create(
            shopify_order_id=order_id,
            defaults={
                "email": order_data.get("email"),
                "total_price": Decimal(order_data.get("total_price", "0")),
                "raw_data": order_data
            }
        )

        if created:
            print("Order created in DB")
        else:
            print("Order already exists")

        return HttpResponse(status=200)

    except Exception as e:
        print("ERROR saving order:", str(e))
        return HttpResponse(status=500)