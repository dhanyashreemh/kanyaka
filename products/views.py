import requests
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms
from .models import Product
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import tempfile
from .forms import ProductForm
from django.contrib import messages
from decimal import Decimal
from business.models import GoldRate   
import json
import hmac
import hashlib
import base64 
from business.views import calculate_price
from .utils import cleanup_old_webhooks
from .models import WebhookLog



class CSVUploadForm(forms.Form):
    file = forms.FileField()


#Get Online Store Publication ID
def get_online_store_publication_id():
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    {
      publications(first: 10) {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """

    response = requests.post(url, json={"query": query}, headers=headers)
    data = response.json()

    print("PUBLICATION RESPONSE:", data)

    publications = data.get("data", {}).get("publications")

    if not publications:
        return None

    for pub in publications["edges"]:
        if pub["node"]["name"] == "Online Store":
            return pub["node"]["id"]

    return None


def update_inventory_item(inventory_item_id, sku=None, barcode=None):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    mutation = """
    mutation inventoryItemUpdate($input: InventoryItemInput!) {
      inventoryItemUpdate(input: $input) {
        inventoryItem {
          id
          sku
          barcode
        }
        userErrors {
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "id": inventory_item_id,
            "sku": sku or "",
            "barcode": barcode or ""
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json={"query": mutation, "variables": variables}
    )

    print("✅ SKU/BARCODE UPDATED:", response.json())


#publishes the product to Online Store.
def publish_product_to_online_store(product_id):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    publication_id = get_online_store_publication_id()

    mutation = f"""
    mutation {{
      publishablePublish(
        id: "{product_id}",
        input: {{
          publicationId: "{publication_id}"
        }}
      ) {{
        userErrors {{
          message
        }}
      }}
    }}
    """

    response = requests.post(url, json={"query": mutation}, headers=headers)

    print("Publish response:", response.json())


# SHOPIFY GRAPHQL FUNCTION
# ----------------------------
def create_product_shopify(
    title,
    description,
    price,
    collection=None,
    compare_price=None,
    jewelry_type=None,
    metal_type=None,
    stone_type=None,
    purity=None,
    occasion=None,
    weight=None,
    quantity=0,
    sku=None,
    tags=None,
    barcode=None,
    cost_per_item=None,
    unit_price=None,
    charge_tax=False,
    inventory_tracked=False,
    sell_out_of_stock=False,
    image_url=None
):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    # Convert tags string → list
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # -------------------------
    # Step 1: Create Product
    # -------------------------
    create_query = """
    mutation productCreate($input: ProductCreateInput!) {
      productCreate(product: $input) {
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
    """

    variables = {
        "input": {
            "title": title,
            "descriptionHtml": description or "",
            "status": "ACTIVE",
            "tags": tag_list,
        }
    }

    response = requests.post(url, headers=headers, json={"query": create_query, "variables": variables})
    data = response.json()
    print("PRODUCT CREATE RESPONSE:", data)

    if "errors" in data:
        raise Exception(f"Shopify API Error: {data['errors']}")

    if not data.get("data") or not data["data"]["productCreate"]["product"]:
        raise Exception(f"Shopify product creation failed: {data}")

    product_data = data["data"]["productCreate"]["product"]
    product_id = product_data["id"]
    variant_id = product_data["variants"]["edges"][0]["node"]["id"]

    # -------------------------
    # Step 2: Update Variant (price, sku, barcode, tax, inventory etc.)
    # -------------------------
    update_query = """
    mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants {
          id
          price
          compareAtPrice
          sku
          barcode
          taxable
          inventoryPolicy
          inventoryItem {
            tracked
          }
        }
        userErrors {
          message
        }
      }
    }
    """

    variant_input = {
        "id": variant_id,
        "price": str(price),
        "compareAtPrice": str(compare_price) if compare_price else None,
        "taxable": charge_tax,
        "inventoryPolicy": "CONTINUE" if sell_out_of_stock else "DENY",
        "inventoryItem": {
            "tracked": inventory_tracked,
            "cost": str(cost_per_item) if cost_per_item else None,
        }
    }

    # Add weight if provided
    if weight:
        variant_input["inventoryItem"]["measurement"] = {
            "weight": {
                "value": float(weight),
                "unit": "GRAMS"
            }
        }

    update_response = requests.post(
        url,
        headers=headers,
        json={
            "query": update_query,
            "variables": {
                "productId": product_id,
                "variants": [variant_input]
            }
        }
    )
    print("VARIANT UPDATE RESPONSE:", update_response.json())

    # -------------------------
    # Step 3: Set Inventory Quantity
    # -------------------------
    if inventory_tracked and quantity:

        # Get inventory item id
        inv_query = """
        query getVariant($id: ID!) {
          productVariant(id: $id) {
            inventoryItem {
              id
            }
          }
        }
        """
        inv_response = requests.post(url, headers=headers, json={"query": inv_query, "variables": {"id": variant_id}})
        inv_data = inv_response.json()
        print("INVENTORY ITEM RESPONSE:", inv_data)
        inventory_item_id = inv_data["data"]["productVariant"]["inventoryItem"]["id"]
        update_inventory_item(
            inventory_item_id,
            sku=sku,
            barcode=barcode
        )

        # Get first location id
        
        loc_query = "{ locations(first: 1) { edges { node { id } } } }"
        loc_response = requests.post(url, headers=headers, json={"query": loc_query})
        loc_data = loc_response.json()
        print("LOCATION RESPONSE:", loc_data)

        locations = loc_data.get("data", {}).get("locations", {}).get("edges", [])
        if not locations:
            print("WARNING: No locations found, skipping inventory quantity set")
        else:
            location_id = locations[0]["node"]["id"]

            # Set quantity
            qty_mutation = """
            mutation setQuantity($input: InventorySetQuantitiesInput!) {
              inventorySetQuantities(input: $input) {
                userErrors { message }
              }
            }
            """
            qty_variables = {
                "input": {
                    "reason": "correction",
                    "name": "available",
                    "ignoreCompareQuantity": True,
                    "quantities": [{
                        "inventoryItemId": inventory_item_id,
                        "locationId": location_id,
                        "quantity": quantity
                    }]
                }
            }
            qty_response = requests.post(url, headers=headers, json={"query": qty_mutation, "variables": qty_variables})
            print("QUANTITY SET RESPONSE:", qty_response.json())
  
        
    # -------------------------
    # Step 4: Add Image
    # -------------------------
    if image_url:
        image_query = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
          productCreateMedia(productId: $productId, media: $media) {
            media {
              mediaContentType
              alt
            }
            mediaUserErrors {
              message
            }
          }
        }
        """
        image_variables = {
            "productId": product_id,
            "media": [{
                "mediaContentType": "IMAGE",
                "originalSource": image_url
            }]
        }
        img_response = requests.post(url, headers=headers, json={"query": image_query, "variables": image_variables})
        print("IMAGE RESPONSE:", img_response.json())

    # -------------------------
    # Step 5: Save to Database
    # -------------------------
   
    publish_product_to_online_store(product_id)

    return {
      "product_id": product_id,
      "variant_id": variant_id
    }


# ----------------------------
# MANUAL PRODUCT UPLOAD
# ----------------------------

from decimal import Decimal



@login_required
def manual_product_upload(request):

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            print("✅ FORM VALID")

            product = form.save(commit=False)

            # =========================
            # 💰 PRICE CALCULATION (FIXED)
            # =========================
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

            # =========================
            # 🛒 SHOPIFY SYNC (SAFE)
            # =========================
            try:
                shopify_data = create_product_shopify(
                    title=product.title,
                    description=product.description,
                    price=float(product.price),  # Shopify expects float
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

                if shopify_data:
                    product.shopify_product_id = shopify_data.get("product_id")
                    product.shopify_variant_id = shopify_data.get("variant_id")

            except Exception as e:
                print("❌ Shopify Error:", e)
                messages.error(request, f"Shopify error: {str(e)}")
                return render(request, "products/manual_upload.html", {"form": form})

            # =========================
            # 💾 SAVE TO DB
            # =========================
            Product.objects.update_or_create(
              shopify_product_id=product.shopify_product_id,
              defaults={
                  "title": product.title,
                  "description": product.description,
                  "price": product.price,
                  "compare_price": product.compare_price,
                  "collection": product.collection,
                  "jewelry_type": product.jewelry_type,
                  "metal_type": product.metal_type,
                  "stone_type": product.stone_type,
                  "purity": product.purity,
                  "occasion": product.occasion,
                  "weight": product.weight,
                  "quantity": product.quantity,
                  "sku": product.sku,
                  "tags": product.tags,
                  "barcode": product.barcode,
                  "cost_per_item": product.cost_per_item,
                  "unit_price": product.unit_price,
                  "charge_tax": product.charge_tax,
                  "inventory_tracked": product.inventory_tracked,
                  "sell_out_of_stock": product.sell_out_of_stock,
                  "shopify_variant_id": product.shopify_variant_id,
              }
          )

            messages.success(request, "✅ Product created successfully!")
            return redirect("staff_products")

        else:
            print("❌ FORM ERRORS:", form.errors)
            messages.error(request, form.errors)

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

            # ✅ Read CSV (tab-separated fix included)
            decoded_file = file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)

            # auto detect delimiter (comma or tab)
            sample = decoded_file[:1024]
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.DictReader(io_string, dialect=dialect)

            success_count = 0
            error_count = 0

            for row in reader:
                try:
                    # ✅ CLEAN DATA
                    title = row.get("title")
                    description = row.get("description")
                    rate_obj = GoldRate.objects.last()

                    weight = Decimal(row.get("weight") or 0)

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

                    # Convert booleans safely
                    def to_bool(val):
                        return str(val).strip().lower() in ["true", "1", "yes"]

                    shopify_data = create_product_shopify(
                        title=title,
                        description=description,
                        price=price,
                        compare_price=row.get("compare_price") or None,
                        collection=row.get("collection"),
                        jewelry_type=row.get("jewelry_type"),
                        metal_type=row.get("metal_type"),
                        stone_type=row.get("stone_type"),
                        purity=row.get("purity"),
                        occasion=row.get("occasion"),
                        weight=float(row.get("weight") or 0),
                        quantity=int(float(row.get("quantity") or 0)),
                        sku=row.get("sku"),
                        tags=row.get("tags"),
                        barcode=row.get("barcode"),
                        cost_per_item=row.get("cost_per_item"),
                        unit_price=row.get("unit_price"),
                        charge_tax=to_bool(row.get("charge_tax")),
                        inventory_tracked=to_bool(row.get("inventory_tracked")),
                        sell_out_of_stock=to_bool(row.get("sell_out_of_stock")),
                    )

                    # ✅ SAVE TO DB
                    Product.objects.update_or_create(
                        shopify_product_id=shopify_data.get("product_id"),
                        defaults={
                            "title": title,
                            "description": description,
                            "price": price,
                            "compare_price": row.get("compare_price"),
                            "collection": row.get("collection"),
                            "jewelry_type": row.get("jewelry_type"),
                            "metal_type": row.get("metal_type"),
                            "stone_type": row.get("stone_type"),
                            "purity": row.get("purity"),
                            "occasion": row.get("occasion"),
                            "weight": row.get("weight"),
                            "quantity": row.get("quantity"),
                            "sku": row.get("sku"),
                            "tags": row.get("tags"),
                            "barcode": row.get("barcode"),
                            "cost_per_item": row.get("cost_per_item"),
                            "unit_price": row.get("unit_price"),
                            "charge_tax": to_bool(row.get("charge_tax")),
                            "inventory_tracked": to_bool(row.get("inventory_tracked")),
                            "sell_out_of_stock": to_bool(row.get("sell_out_of_stock")),
                            "shopify_variant_id": shopify_data.get("variant_id"),
                        }
                    )

                    success_count += 1

                except Exception as e:
                    print("❌ Error:", e)
                    error_count += 1

            messages.success(
                request,
                f"✅ Bulk upload completed! Success: {success_count}, Failed: {error_count}"
            )

            return redirect("sync_shopify_products")

    else:
        form = CSVUploadForm()

    return render(request, "products/bulk_upload.html", {"form": form})

@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})


def sync_shopify_products(request):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/products.json?limit=250"
    headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()

        print("PRODUCT COUNT:", len(data.get("products", [])))

        for product in data.get("products", []):

            product_gid = f"gid://shopify/Product/{product['id']}"

            # Fetch metafields per product
            metafields = get_shopify_metafields(product_gid)

            weight        = safe_decimal(metafields.get("gold_weight"))
            purity        = metafields.get("gold_purity")
            stone_type    = metafields.get("stone_type")
            cost_per_item = safe_decimal(metafields.get("making_charge"))

            for variant in product.get("variants", []):
                Product.objects.update_or_create(
                    shopify_variant_id=variant["id"],
                    defaults={
                        # IDs
                        "shopify_product_id": product_gid,

                        # Basic Info
                        "title":       product.get("title"),
                        "description": product.get("body_html"),

                        # Pricing
                        "price":         safe_decimal(variant.get("price"), Decimal("0")),
                        "compare_price": safe_decimal(variant.get("compare_at_price")),

                        # Classification
                        "collection": product.get("product_type") or "General",
                        "tags":       product.get("tags"),

                        # Jewelry (from metafields)
                        "weight":        weight,
                        "purity":        purity,
                        "stone_type":    stone_type,
                        "cost_per_item": cost_per_item,

                        # ❌ jewelry_type, metal_type, occasion → Django master, never touch here

                        # Inventory
                        "sku":     variant.get("sku"),
                        "barcode": variant.get("barcode"),
                        "quantity": variant.get("inventory_quantity", 0),

                        "inventory_tracked": variant.get("inventory_management") == "shopify",
                        "sell_out_of_stock": variant.get("inventory_policy") == "continue",
                        "charge_tax":        variant.get("taxable", True),

                        # Raw backup
                        "raw_data": product,
                    }
                )
                print(f"✅ Synced: {product['title']} (Variant: {variant['id']})")

        link_header = response.headers.get("Link")
        if link_header and 'rel="next"' in link_header:
            url = link_header.split(";")[0].strip("<> ")
        else:
            url = None

    print("🚀 Sync completed")
    return redirect("staff_products")

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
        product.unit_price    = request.POST.get("unit_price")    or None
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

        update_product_shopify(product)
        product.save()

        messages.success(request, f'"{product.title}" updated successfully.')
        return redirect("staff_products")

    return render(request, "staff/edit_product.html", {"product": product})


# REPLACE delete_product

@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)  

    if request.method == "POST":
        delete_product_shopify(product)
        product.delete()
        messages.success(request, "🗑️ Product deleted successfully.")
        return redirect("staff_products")

    return render(request, "staff/delete_product.html", {"product": product})


def update_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    product_id = product.shopify_product_id
    variant_id = product.shopify_variant_id

    if not product_id or not variant_id:
        print(f"❌ Missing Shopify IDs for {product.title}")
        return

    price = float(product.price or 0)
    weight = float(product.weight or 0)

    if not weight:
      print(f"❌ Missing weight → skipping {product.title}")
      return

    title = str(product.title)

    # 1️⃣ Title update
    mutation = f"""
    mutation {{
      productUpdate(input: {{
        id: "{product_id}",
        title: "{title}"
      }}) {{
        userErrors {{ message }}
      }}
    }}
    """
    print("TITLE:", requests.post(url, json={"query": mutation}, headers=headers).json())

    # 2️⃣ Price + weight
    variant_mutation = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{product_id}",
        variants: [{{
            id: "{variant_id}",
            price: "{price}",
            inventoryItem: {{
              measurement: {{
                weight: {{
                  value: {weight},
                  unit: GRAMS
                }}
              }}
            }}
        }}]
      ) {{
        userErrors {{ message }}
      }}
    }}
    """
    print("VARIANT:", requests.post(url, json={"query": variant_mutation}, headers=headers).json())

    update_product_metafields(product)



def update_product_metafields(product):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    mutation = f"""
    mutation {{
      metafieldsSet(metafields: [

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "gold_weight",
          type: "number_decimal",
          value: "{product.weight or 0}"
        }},

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "gold_purity",
          type: "single_line_text_field",
          value: "{product.purity or ''}"
        }},

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "stone_type",
          type: "single_line_text_field",
          value: "{product.stone_type or ''}"
        }},

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "making_charge",
          type: "number_decimal",
          value: "{product.cost_per_item or 0}"
        }},

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "size",
          type: "single_line_text_field",
          value: "{product.collection or ''}"
        }},

        {{
          ownerId: "{product.shopify_product_id}",
          namespace: "custom",
          key: "delivery_time",
          type: "single_line_text_field",
          value: "5-7 days"
        }}

      ]) {{
        userErrors {{
          message
        }}
      }}
    }}
    """

    requests.post(url, json={"query": mutation}, headers=headers)

def delete_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    product_id = product.shopify_product_id

    mutation = f"""
    mutation {{
      productDelete(input: {{
        id: "{product_id}"
      }}) {{
        deletedProductId
        userErrors {{
          message
        }}
      }}
    }}
    """

    requests.post(url, json={"query": mutation}, headers=headers)

#Generate JSONL From CSV

def generate_jsonl_from_csv(file):
    decoded_file = file.read().decode("utf-8")
    io_string = io.StringIO(decoded_file)
    reader = list(csv.DictReader(io_string, delimiter='\t'))

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")

    for row in reader:
        data = {
            "input": {
                "title": row["title"],
                "descriptionHtml": row["description"],
            }
        }
        temp.write((json.dumps(data) + "\n").encode("utf-8"))

    temp.close()
    return temp.name

#Create Staged Upload

def create_staged_upload():
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    mutation {
      stagedUploadsCreate(input: {
        resource: BULK_MUTATION_VARIABLES,
        filename: "bulk_products.jsonl",
        mimeType: "text/jsonl",
        httpMethod: POST
      }) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
      }
    }
    """

    response = requests.post(url, json={"query": query}, headers=headers)
    return response.json()["data"]["stagedUploadsCreate"]["stagedTargets"][0]

#Upload JSONL to Shopify
def upload_jsonl_to_shopify(target, file_path):
    upload_url = target["url"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(upload_url, data=params, files=files)

    print("Upload status code:", response.status_code)
    print("Upload response text:", response.text)

    # Google storage returns 201
    return response.status_code in [200, 201, 204]

#Run Bulk Operation
def run_bulk_operation(staged_path):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    mutation = f"""
    mutation {{
      bulkOperationRunMutation(
        mutation: \"\"\"
        mutation ($input: ProductInput!) {{
          productCreate(input: $input) {{
            product {{
              id
              title
            }}
            userErrors {{
              field
              message
            }}
          }}
        }}
        \"\"\",
        stagedUploadPath: "{staged_path}"
      ) {{
        bulkOperation {{
          id
          status
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """

    response = requests.post(url, json={"query": mutation}, headers=headers)
    data = response.json()

    print("🔥 BULK RUN RESPONSE:", data)

    return data

#Check Bulk Status
def check_bulk_status():
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    {
      currentBulkOperation {
        id
        status
        errorCode
        objectCount
        url
      }
    }
    """

    response = requests.post(url, json={"query": query}, headers=headers)

    try:
        data = response.json()

        # Debug print
        print("BULK STATUS RESPONSE:", data)

        if "data" in data and data["data"]["currentBulkOperation"]:
            return data["data"]["currentBulkOperation"]

        return None

    except Exception as e:
        print("Bulk status error:", e)
        return None
    

#Bulk Status View
from django.http import JsonResponse

@login_required
def bulk_status_view(request):
    status_data = check_bulk_status()

    if not status_data:
        return JsonResponse({
            "status": "NO_ACTIVE_JOB",
            "message": "No active bulk operation."
        })

    return JsonResponse(status_data)


#Download Result When Completed
def download_bulk_result(result_url):
    response = requests.get(result_url)
    with open("bulk_result.jsonl", "wb") as f:
        f.write(response.content)


def get_shopify_metafields(product_gid):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"
    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    query getMetafields($id: ID!) {
      product(id: $id) {
        metafields(first: 20, namespace: "custom") {
          edges {
            node {
              key
              value
            }
          }
        }
      }
    }
    """

    response = requests.post(url, json={"query": query, "variables": {"id": product_gid}}, headers=headers)
    data = response.json()

    metafields = {}
    edges = data.get("data", {}).get("product", {}).get("metafields", {}).get("edges", [])
    for edge in edges:
        node = edge["node"]
        metafields[node["key"]] = node["value"]

    print("📦 Metafields:", metafields)
    return metafields


def safe_decimal(value, default=None):
    try:
        return Decimal(str(value)) if value else default
    except Exception:
        return default

#Receives Shopify webhook↓Extracts product data !Updates Django DB
@csrf_exempt
def shopify_product_webhook(request):
    # 🧹 cleanup old webhook logs
    cleanup_old_webhooks()
    try:
        received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
        secret = settings.SHOPIFY_WEBHOOK_SECRET

        calculated_hmac = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                request.body,
                hashlib.sha256
            ).digest()
        ).decode()

        if not received_hmac or not hmac.compare_digest(received_hmac, calculated_hmac):
            print("❌ HMAC verification failed")
            return HttpResponse(status=401)

        print("✅ PRODUCT WEBHOOK VERIFIED")


        webhook_id = request.headers.get("X-Shopify-Webhook-Id")

        if WebhookLog.objects.filter(webhook_id=webhook_id).exists():
            print("⚠️ Duplicate webhook skipped")
            return HttpResponse(status=200)

        # Save webhook
        WebhookLog.objects.create(
            webhook_id=webhook_id,
            topic=request.headers.get("X-Shopify-Topic")
        )

        topic = request.headers.get("X-Shopify-Topic")
        data = json.loads(request.body)

        print("🔥 WEBHOOK:", topic)

        if topic in ["products/create", "products/update"]:

            raw_product_id = data.get("id")
            product_gid = f"gid://shopify/Product/{raw_product_id}"

            # Fetch metafields from Shopify
            metafields = get_shopify_metafields(product_gid)

            weight        = safe_decimal(metafields.get("gold_weight"))
            purity        = metafields.get("gold_purity")
            stone_type    = metafields.get("stone_type")
            cost_per_item = safe_decimal(metafields.get("making_charge"))

            for variant in data.get("variants", []):
                variant_id = variant.get("id")

                if not variant_id:
                    print("❌ Missing variant ID")
                    continue

                try:
                    Product.objects.update_or_create(
                        shopify_variant_id=variant_id,
                        defaults={
                            # IDs
                            "shopify_product_id": product_gid,

                            # Basic Info
                            "title":       data.get("title"),
                            "description": data.get("body_html"),

                            # Pricing
                            "price":         safe_decimal(variant.get("price"), Decimal("0")),
                            "compare_price": safe_decimal(variant.get("compare_at_price")),

                            # Classification
                            "collection": data.get("product_type"),
                            "tags":       data.get("tags"),

                            # Jewelry (from metafields)
                            "weight":        weight,
                            "purity":        purity,
                            "stone_type":    stone_type,
                            "cost_per_item": cost_per_item,

                            # ❌ jewelry_type, metal_type, occasion → Django master, never touch here

                            # Inventory
                            "sku":      variant.get("sku"),
                            "barcode":  variant.get("barcode"),
                            "quantity": variant.get("inventory_quantity") or 0,

                            "inventory_tracked":  variant.get("inventory_management") == "shopify",
                            "sell_out_of_stock":  variant.get("inventory_policy") == "continue",
                            "charge_tax":         variant.get("taxable", True),

                            # Raw backup
                            "raw_data": data,
                        }
                    )
                    print(f"✅ Synced variant {variant_id}")

                except Exception as e:
                    print(f"❌ Error saving variant {variant_id}: {str(e)}")

        elif topic == "products/delete":
          print("⚠️ Delete webhook received")

          product_id = data.get("id")
          product_gid = f"gid://shopify/Product/{product_id}"

          deleted_count, _ = Product.objects.filter(
              shopify_product_id=product_gid
          ).delete()

          print(f"🗑️ Deleted {deleted_count} records")

        return HttpResponse(status=200)

    except Exception as e:
        print("❌ WEBHOOK ERROR:", str(e))
        return HttpResponse(status=500)
    
#helper to fetch metafields
# def get_product_metafields(product_id):
#     url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/products/{product_id}/metafields.json"

#     headers = {
#         "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN
#     }

#     res = requests.get(url, headers=headers)
#     return res.json().get("metafields", [])



# def extract_gold_weight(metafields):
#     for mf in metafields:
#         # adjust if namespace exists (recommended)
#         if mf.get("key") in ["gold_weight", "Gold Weight"]:
#             try:
#                 return float(mf.get("value", 0))
#             except:
#                 return 0
#     return 0



#CREATE METAFIELD FUNCTION
# def update_gold_weight_metafield(product_id, weight):
#     url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

#     headers = {
#         "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
#         "Content-Type": "application/json"
#     }

#     mutation = f"""
#     mutation {{
#       metafieldsSet(metafields: [{{
#         ownerId: "{product_id}",
#         namespace: "custom",
#         key: "gold_weight",
#         type: "number_decimal",
#         value: "{weight}"
#       }}]) {{
#         userErrors {{
#           message
#         }}
#       }}
#     }}
#     """

#     res = requests.post(url, json={"query": mutation}, headers=headers)
#     print("Metafield update:", res.json())


    
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "staff/product_detail.html", {"product": product})





