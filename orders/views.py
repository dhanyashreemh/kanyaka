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

    # TEMP: Disable verification
    # if not verify_webhook(request):
    #     return HttpResponse(status=401)

    try:
        if not request.body:
            return HttpResponse("Empty body", status=400)

        order_data = json.loads(request.body)

        print("Formatted Order Data:")
        print(json.dumps(order_data, indent=4))

        order_id = order_data.get("id")

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