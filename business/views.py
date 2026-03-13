from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import GoldRate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from orders.models import Order
from products.models import Product

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

        rate_24k = request.POST.get("rate_24k")
        rate_22k = request.POST.get("rate_22k")
        making_charge = request.POST.get("making_charge")
        gst = request.POST.get("gst")

        GoldRate.objects.create(
            rate_24k=rate_24k,
            rate_22k=rate_22k,
            making_charge_per_gram=making_charge,
            gst_percentage=gst
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
    

    

