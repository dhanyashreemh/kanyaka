import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order
from .utils import verify_webhook

@csrf_exempt
def shopify_webhook(request):

    print("Webhook hit")

    if request.method != "POST":
        return HttpResponse(status=405)

    if not verify_webhook(request):
        print("HMAC verification failed")
        return HttpResponse(status=401)

    try:
        print("Raw body:", request.body)

        order_data = json.loads(request.body)

        # 👇 PUT IT RIGHT HERE
        order_id = order_data.get("id")
        if not order_id:
            print("No ID found in payload")
            return HttpResponse(status=400)

        print("Order ID:", order_id)

        Order.objects.get_or_create(
            shopify_order_id=order_id,
            defaults={
                "email": order_data.get("email"),
                "total_price": order_data.get("total_price"),
                "raw_data": order_data
            }
        )

        print("Order saved successfully")
        return HttpResponse(status=200)

    except Exception as e:
        print("ERROR:", str(e))
        return HttpResponse(status=400)