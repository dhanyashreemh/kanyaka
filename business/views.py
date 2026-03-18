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

def calculate_price(weight, stone, rate22, making, gst):

    gold_value = weight * rate22
    making_cost = weight * making

    subtotal = gold_value + making_cost + stone
    tax = subtotal * (gst / 100)

    total = subtotal + tax

    return round(total)


#Update Rate View

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

        # ✅ Save new rate
        rate_obj = GoldRate.objects.create(
            rate_24k=rate_24k,
            rate_22k=rate_22k,
            making_charge_per_gram=making,   # ✅ correct
            gst_percentage=gst               # ✅ correct
        )
        rate_obj.making_type = making_type
        rate_obj.save()

        products = Product.objects.all()

        for product in products:

            try:
                weight = float(product.weight or 0)
                stone = float(getattr(product, "stone_price", 0) or 0)

                if weight <= 0:
                    print(f"⚠️ Skipping {product.title} (no weight)")
                    continue

                # 💰 Base price
                base_price = weight * rate_obj.rate_22k

                # 🔥 SAME LOGIC AS MANUAL UPLOAD
                if rate_obj.making_type == "percent":
                    making_cost = base_price * (rate_obj.making_charge_per_gram / 100)
                else:
                    making_cost = weight * rate_obj.making_charge_per_gram

                subtotal = base_price + making_cost + stone
                gst_amount = subtotal * (rate_obj.gst_percentage / 100)

                total_price = round(subtotal + gst_amount, 2)

                # ✅ Save to DB
                product.price = total_price
                product.save()

                # 🚀 Update Shopify
                if product.shopify_variant_id:
                    update_product_price(
                        product.shopify_variant_id,
                        total_price
                    )

                print(f"✅ Updated {product.title} → ₹{total_price}")

            except Exception as e:
                print(f"❌ Error updating {product.title}: {str(e)}")

        return redirect("dashboard")


@login_required
def staff_orders(request):
    orders = Order.objects.all().order_by("-id")
    return render(request, "staff/orders.html", {"orders": orders})


@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})
    

    

