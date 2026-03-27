import requests
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms
from .models import Product
from .forms import ProductForm
from django.contrib import messages
from decimal import Decimal
from business.models import GoldRate
from django.core.cache import cache   
from business.pricing import calculate_price
from products.services.product import (
    create_product_shopify,
    update_product_shopify,
    delete_product_shopify
)

from products.services.shopify_bulk import (
    check_bulk_status
)
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from products.services.shopify_sync import sync_products_service
import logging
from django.db.models import Q
from products.services.webhook_service import handle_shopify_webhook

logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 60 * 5


class CSVUploadForm(forms.Form):
    file = forms.FileField()

@login_required
def manual_product_upload(request):

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            logger.info("✅ Form validated")

            product = form.save(commit=False)

            # 💰 PRICE
            rate_obj = GoldRate.objects.last()

            if rate_obj and product.weight:
                product.price = calculate_price(
                    weight=product.weight,
                    rate22=rate_obj.rate_22k,
                    making=rate_obj.making_charge_per_gram,
                    gst=rate_obj.gst_percentage,
                    making_type=rate_obj.making_type,
                    stone=product.cost_per_item
                )
            else:
                product.price = Decimal(0)

            # 🚀 CACHE (prevent double submit)
            cache_key = f"manual_{product.title}_{product.weight}"

            if cache.get(cache_key):
                logger.warning(f"⚠️ Duplicate blocked: {cache_key}")
                messages.warning(request, "Duplicate request blocked")
                return redirect("staff_products")

            cache.set(cache_key, True, timeout=CACHE_TIMEOUT)

            try:
                logger.info(f"🆕 Creating product: {product.title}")

                shopify_data = create_product_shopify(
                    title=product.title,
                    description=product.description,
                    price=float(product.price),
                    compare_price=product.compare_price,
                    collection=product.collection,
                    jewelry_type=product.jewelry_type,
                    metal_type=product.metal_type,
                    stone_type=product.stone_type,
                    purity=product.purity,
                    occasion=product.occasion,
                    weight=float(product.weight or 0),
                    quantity=product.quantity,
                    sku=product.sku,
                    tags=product.tags,
                    barcode=product.barcode,
                    cost_per_item=product.cost_per_item,
                    unit_price=product.unit_price,
                    charge_tax=product.charge_tax,
                    inventory_tracked=product.inventory_tracked,
                    sell_out_of_stock=product.sell_out_of_stock,
                )

                # ✅ attach IDs
                product.shopify_product_id = shopify_data.get("product_id")
                product.shopify_variant_id = shopify_data.get("variant_id")

                from business.shopify_service import sync_images_to_shopify

                images = request.FILES.getlist("images")

                if images:

                    for img in images:
                        product.image = img
                        product.save()

                        # 🔥 AUTO URL (no error now)
                        product.image_url = request.build_absolute_uri(product.image.url)
                        product.save()

                        # 🔥 Shopify sync
                        from business.shopify_service import sync_images_to_shopify
                        sync_images_to_shopify(product)

                logger.info(f"✅ Shopify created: {product.shopify_product_id}")

            except Exception as e:
                logger.error("❌ Shopify error", exc_info=True)
                messages.error(request, str(e))
                return render(request, "products/manual_upload.html", {"form": form})

            # ✅ SINGLE SAVE (IMPORTANT)
            product.save()

            logger.info(f"💾 Saved: {product.title}")

            messages.success(request, "✅ Product created!")
            return redirect("staff_products")

        else:
            logger.warning(f"❌ Form error: {form.errors}")
            messages.error(request, form.errors)

    else:
        form = ProductForm()

    return render(request, "products/manual_upload.html", {"form": form})



@login_required
def bulk_product_upload(request):

    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            file = request.FILES["file"]

            decoded_file = file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)

            reader = csv.DictReader(io_string)

            success_count = 0
            update_count = 0
            error_count = 0

            rate_obj = GoldRate.objects.last()

            for row in reader:
                try:
                    title = row.get("title")
                    weight = Decimal(row.get("weight") or 0)

                    # 💰 PRICE
                    if rate_obj and weight:
                        price = calculate_price(
                            weight=weight,
                            rate22=rate_obj.rate_22k,
                            making=rate_obj.making_charge_per_gram,
                            gst=rate_obj.gst_percentage,
                            making_type=rate_obj.making_type,
                            stone=Decimal(row.get("cost_per_item") or 0)
                        )
                    else:
                        price = Decimal(0)

                    cache_key = f"bulk_{title}_{weight}"

                    if cache.get(cache_key):
                        logger.warning(f"⚠️ Skipped duplicate: {title}")
                        continue

                    cache.set(cache_key, True, timeout=CACHE_TIMEOUT)

                    # 🔍 Find existing product
                    product = Product.objects.filter(title=title).first()

                    if product and product.shopify_product_id:
                        # 🔄 UPDATE
                        logger.info(f"🔄 Updating: {title}")

                        product.price = price
                        product.weight = weight
                        product.quantity = int(row.get("quantity") or 0)

                        product.save()
                        update_product_shopify(product)

                        update_count += 1

                    else:
                        # 🆕 CREATE
                        logger.info(f"🆕 Creating: {title}")

                        shopify_data = create_product_shopify(
                            title=title,
                            description=row.get("description"),
                            price=float(price),
                            compare_price=row.get("compare_price") or None,
                            collection=row.get("collection"),
                            jewelry_type=row.get("jewelry_type"),
                            metal_type=row.get("metal_type"),
                            stone_type=row.get("stone_type"),
                            purity=row.get("purity"),
                            occasion=row.get("occasion"),
                            weight=float(weight),
                            quantity=int(row.get("quantity") or 0),
                            sku=row.get("sku"),
                            tags=row.get("tags"),
                            barcode=row.get("barcode"),
                            cost_per_item=row.get("cost_per_item"),
                            unit_price=row.get("unit_price"),
                            charge_tax=str(row.get("charge_tax")).lower() in ["true", "1"],
                            inventory_tracked=str(row.get("inventory_tracked")).lower() in ["true", "1"],
                            sell_out_of_stock=str(row.get("sell_out_of_stock")).lower() in ["true", "1"],
                        )

                        Product.objects.create(
                            title=title,
                            description=row.get("description"),
                            price=price,
                            weight=weight,
                            quantity=row.get("quantity"),
                            shopify_product_id=shopify_data.get("product_id"),
                            shopify_variant_id=shopify_data.get("variant_id"),
                        )

                        success_count += 1

                except Exception as e:
                    logger.error(f"❌ Bulk error: {row}", exc_info=True)
                    error_count += 1

            messages.success(
                request,
                f"✅ Bulk Done | Created: {success_count}, Updated: {update_count}, Failed: {error_count}"
            )

            return redirect("staff_products")

    else:
        form = CSVUploadForm()

    return render(request, "products/bulk_upload.html", {"form": form})

@login_required
# views.py
def staff_products(request):
    query = request.GET.get('q')

    if query:
        filters = Q(title__icontains=query)

        if query.isdigit():
            filters |= Q(id=int(query))

        products = Product.objects.filter(filters)
    else:
        products = Product.objects.all()

    return render(request, 'staff/products.html', {
        'products': products
    })

@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        # Basic Info
        product.title         = request.POST.get("title")
        product.description   = request.POST.get("description")
        product.collection    = request.POST.get("collection")
        product.tags          = request.POST.get("tags")

        # Pricing
        product.price         = request.POST.get("price")
        product.compare_price = request.POST.get("compare_price") or None
        product.unit_price    = request.POST.get("unit_price") or None
        product.cost_per_item = request.POST.get("cost_per_item") or None
        product.charge_tax    = request.POST.get("charge_tax") == "on"

        # Jewelry Details
        product.jewelry_type  = request.POST.get("jewelry_type")
        product.metal_type    = request.POST.get("metal_type")
        product.stone_type    = request.POST.get("stone_type")
        product.purity        = request.POST.get("purity")
        product.occasion      = request.POST.get("occasion")
        product.weight        = request.POST.get("weight") or None

        # Inventory
        product.sku               = request.POST.get("sku")
        product.barcode           = request.POST.get("barcode")
        product.quantity          = request.POST.get("quantity") or 0
        product.inventory_tracked = request.POST.get("inventory_tracked") == "on"
        product.sell_out_of_stock = request.POST.get("sell_out_of_stock") == "on"

        # 🖼️ IMAGE HANDLING
        image = request.FILES.get("image")

        if image:
            product.image = image
            product.save()

            product.image_url = request.build_absolute_uri(product.image.url)
            product.save()

        # ✅ SAVE FIRST
        product.save()

        # 🔥 SHOPIFY SYNC
        from business.shopify_service import (
            update_product_shopify,
            sync_images_to_shopify
        )

        update_product_shopify(product)
        sync_images_to_shopify(product)

        messages.success(request, f'"{product.title}" updated successfully.')
        return redirect("staff_products")

    return render(request, "staff/edit_product.html", {"product": product})

@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)  

    if request.method == "POST":
        delete_product_shopify(product)
        product.delete()
        messages.success(request, "🗑️ Product deleted successfully.")
        return redirect("staff_products")

    return render(request, "staff/delete_product.html", {"product": product})

@login_required
def bulk_status_view(request):
    status_data = check_bulk_status()

    if not status_data:
        return JsonResponse({
            "status": "NO_ACTIVE_JOB",
            "message": "No active bulk operation."
        })

    return JsonResponse(status_data)

def download_bulk_result(result_url):
    response = requests.get(result_url)
    with open("bulk_result.jsonl", "wb") as f:
        f.write(response.content)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "staff/product_detail.html", {"product": product})



def sync_shopify_products(request):
    try:
        result = sync_products_service()

        messages.success(request, "✅ Shopify sync completed!")
        return redirect("staff_products")

    except Exception as e:
        logger.error("Sync failed", exc_info=True)
        messages.error(request, "❌ Sync failed")
        return redirect("staff_products")
    


def shopify_product_webhook(request):
    try:
        data = handle_shopify_webhook(request)

        return JsonResponse({
            "status": "success",
            "message": "Webhook processed",
            "data": data
        })

    except Exception as e:
        logger.error("Webhook failed", exc_info=True)
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)





