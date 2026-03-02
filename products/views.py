import requests
import csv
import io
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms


# ----------------------------
# FORMS
# ----------------------------

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
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2026-01/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "title": title,
            "descriptionHtml": description,
            "variants": [
                {"price": str(price)}
            ]
        }
    }

    requests.post(url, json={"query": query, "variables": variables}, headers=headers)


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