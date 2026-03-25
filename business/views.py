import logging
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import GoldRate
from orders.models import Order
from products.models import Product
from .services import create_gold_rate

logger = logging.getLogger(__name__)

@login_required
def staff_panel(request):
    return render(request, "staff/staffpanel.html")

@login_required
def dashboard(request):
    try:
        rate = GoldRate.objects.latest('updated_at')
    except GoldRate.DoesNotExist:
        rate = None

    return render(request, "staff/dashboard.html", {"rate": rate})


@login_required
def update_rate(request):

    if request.method == "POST":
        try:
            data = {
                "rate_24k": Decimal(request.POST.get("rate_24k", "0")),
                "rate_22k": Decimal(request.POST.get("rate_22k", "0")),
                "making": Decimal(request.POST.get("making_charge", "0")),
                "gst": Decimal(request.POST.get("gst", "0")),
                "making_type": request.POST.get("making_type", "percent")
            }

            create_gold_rate(data)

        except Exception as e:
            logger.error("Failed to update gold rate", exc_info=True)

            messages.error(request, "Something went wrong. Please try again.")
            return redirect("dashboard")

        return redirect("dashboard")


@login_required
def staff_orders(request):
    orders = Order.objects.all().order_by("-id")
    return render(request, "staff/orders.html", {"orders": orders})


@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})