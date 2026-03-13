from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import GoldRate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from orders.models import Order
from products.models import Product
from .shopify_service import get_shopify_products, update_product_price

#staff panel view
from django.contrib.auth.decorators import login_required
@login_required
def staff_panel(request):
    return render(request, "staff/staffpanel.html")

#Dashboard View
@login_required
def dashboard(request):
    rate = GoldRate.objects.order_by('-updated_at').first()
    return render(request, "staff/dashboard.html", {"rate": rate})


#Update Rate View
@login_required
def update_rate(request):

    if request.method == "POST":

        rate_24k = float(request.POST.get("rate_24k"))
        rate_22k = float(request.POST.get("rate_22k"))
        making = float(request.POST.get("making_charge"))
        gst = float(request.POST.get("gst"))

        GoldRate.objects.create(
            rate_24k=rate_24k,
            rate_22k=rate_22k,
            making_charge_per_gram=making,
            gst_percentage=gst
        )

        # Get Shopify products
        products = get_shopify_products()

        for product in products:

            for variant in product["variants"]:

                # Example values (later fetch from metafields)
                weight = 10
                stone = 200

                price = calculate_price(
                    weight,
                    stone,
                    rate_22k,
                    making,
                    gst
                )

                update_product_price(
                    variant["id"],
                    price
                )

        return redirect("dashboard")


@login_required
def staff_orders(request):
    orders = Order.objects.all().order_by("-id")
    return render(request, "staff/orders.html", {"orders": orders})


@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})
    
def calculate_price(weight, stone, rate22, making, gst):

    gold_value = weight * rate22
    making_cost = weight * making

    subtotal = gold_value + making_cost + stone
    tax = subtotal * (gst / 100)

    total = subtotal + tax

    return round(total)
    

