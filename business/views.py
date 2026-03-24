from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import GoldRate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from orders.models import Order
from products.models import Product
from .shopify_service import get_shopify_products, update_product_price
import time
from threading import Thread
from decimal import Decimal

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

from decimal import Decimal

def calculate_price(weight, rate22, making, gst, making_type="fixed", stone=0):
    """
    Universal price calculator for jewelry

    weight       → grams
    rate22       → gold rate per gram
    making       → making charge (percent or per gram)
    gst          → GST %
    making_type  → "percent" or "fixed"
    stone        → extra cost (optional)
    """

    # Safe conversion
    weight = Decimal(weight or 0)
    rate22 = Decimal(rate22 or 0)
    making = Decimal(making or 0)
    gst = Decimal(gst or 0)
    stone = Decimal(stone or 0)

    # Gold value
    gold_value = weight * rate22

    # Making charge
    if making_type == "percent":
        making_cost = gold_value * (making / Decimal(100))
    else:
        making_cost = weight * making

    # Subtotal
    subtotal = gold_value + making_cost + stone

    # GST
    tax = subtotal * (gst / Decimal(100))

    # Final
    total = subtotal + tax

    return round(total, 2)


#Update Rate View

def update_all_products(rate_obj):

    products = Product.objects.exclude(weight__isnull=True)

    for product in products:
        try:
            if not product.weight:
                continue

            new_price = calculate_price(
                weight=product.weight,
                rate22=rate_obj.rate_22k,
                making=rate_obj.making_charge_per_gram,
                gst=rate_obj.gst_percentage,
                making_type=rate_obj.making_type,
                stone=product.cost_per_item
            )

            product.price = new_price
            product.save(update_fields=["price"])

            if product.shopify_variant_id:
                update_product_price(product.shopify_variant_id, float(new_price))
                time.sleep(0.3)  # avoid Shopify rate limit

            print(f"✅ {product.title} → ₹{new_price}")

        except Exception as e:
            print(f"❌ {product.title}: {e}")


# ----------------------------
# 🔥 UPDATE RATE VIEW (OPTIMIZED)
# ----------------------------
@login_required
def update_rate(request):

    if request.method == "POST":

        try:
            rate_24k = float(request.POST.get("rate_24k", 0))
            rate_22k = float(request.POST.get("rate_22k", 0))
            making = float(request.POST.get("making_charge", 0))
            gst = float(request.POST.get("gst", 0))
            making_type = request.POST.get("making_type", "percent")

        except (TypeError, ValueError):
            print("❌ Invalid input")
            return redirect("dashboard")

        # ✅ Save rate
        rate_obj = GoldRate.objects.create(
            rate_24k=rate_24k,
            rate_22k=rate_22k,
            making_charge_per_gram=making,
            gst_percentage=gst
        )
        rate_obj.making_type = making_type
        rate_obj.save()

        print("🚀 Background price update started")

        return redirect("dashboard")


@login_required
def staff_orders(request):
    orders = Order.objects.all().order_by("-id")
    return render(request, "staff/orders.html", {"orders": orders})


@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})
    

    

