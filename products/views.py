import requests
import csv
import io
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms
from .models import Product




class ProductForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea)
    price = forms.DecimalField(max_digits=10, decimal_places=2)


class CSVUploadForm(forms.Form):
    file = forms.FileField()


# ----------------------------
# SHOPIFY GRAPHQL FUNCTION
# ----------------------------
def create_product_shopify(title, description, price):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    create_query = """
    mutation {
      productCreate(product: {
        title: "%s"
        descriptionHtml: "%s"
      }) {
        product {
          id
          title
          variants(first: 1) {
            edges {
              node {
                id
                price
              }
            }
          }
        }
        userErrors {
          message
        }
      }
    }
    """ % (title, description)

    response = requests.post(url, json={"query": create_query}, headers=headers)
    data = response.json()

    print("PRODUCT CREATE RESPONSE:", data)

    product_data = data["data"]["productCreate"]["product"]

    product_id = product_data["id"]
    variant_data = product_data["variants"]["edges"][0]["node"]
    variant_id = variant_data["id"]

    # Update price
    update_query = """
    mutation {
      productVariantsBulkUpdate(
        productId: "%s",
        variants: [{
          id: "%s",
          price: "%s"
        }]
      ) {
        productVariants {
          id
          price
        }
        userErrors {
          message
        }
      }
    }
    """ % (product_id, variant_id, price)

    requests.post(url, json={"query": update_query}, headers=headers)

    # 🔥 SAVE TO DATABASE HERE
    Product.objects.update_or_create(
        shopify_product_id=product_id,
        defaults={
            "title": title,
            "price": price,
            "raw_data": product_data,
        }
    )

    return product_data
# ----------------------------
# MANUAL PRODUCT UPLOAD
# ----------------------------

@login_required
def manual_product_upload(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            create_product_shopify(
                form.cleaned_data["title"],
                form.cleaned_data["description"],
                form.cleaned_data["price"],
            )
            return redirect("staff_panel")
    else:
        form = ProductForm()

    return render(request, "products/manual_upload.html", {"form": form})


# ----------------------------
# BULK CSV UPLOAD
# ----------------------------

@login_required
def bulk_product_upload(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            decoded_file = file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            for row in reader:
                create_product_shopify(
                    row["title"],
                    row["description"],
                    row["price"],
                )

            return redirect("staff_panel")
    else:
        form = CSVUploadForm()

    return render(request, "products/bulk_upload.html", {"form": form})





@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})




