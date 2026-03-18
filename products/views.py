import requests
import csv
import io
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms
from .models import Product
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import tempfile
from .forms import ProductForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


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
        publishable {{
          id
        }}
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
        "sku": sku or "",
        "barcode": barcode or "",
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

    return product_data
# ----------------------------
# MANUAL PRODUCT UPLOAD
# ----------------------------

@login_required
def manual_product_upload(request):

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)

            from .models import GoldRate
            rate_obj = GoldRate.objects.last()

            if rate_obj and product.weight is not None:

                weight = float(product.weight or 0)
                base_price = weight * rate_obj.rate_22k

                making = rate_obj.making_charge

                # ✅ Dynamic making logic
                if rate_obj.making_type == "percent":
                    making_cost = base_price * (making / 100)
                else:
                    making_cost = weight * making

                subtotal = base_price + making_cost
                gst_amount = subtotal * (rate_obj.gst / 100)

                product.price = round(subtotal + gst_amount, 2)

            # 🔥 Shopify call (FIXED comma issue)
            shopify_data = create_product_shopify(
                title=product.title,
                description=product.description,
                price=product.price,
                compare_price=product.compare_price,
                collection=product.collection,
                jewelry_type=product.jewelry_type,
                metal_type=product.metal_type,
                stone_type=product.stone_type,
                purity=product.purity,
                occasion=product.occasion,
                weight=float(product.weight or 0),  # ✅ fixed
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

            # ✅ Save Shopify IDs
            product.shopify_product_id = shopify_data["product_id"]
            product.shopify_variant_id = shopify_data["variant_id"]

            product.save()

            return redirect("staff_products")

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

            # 1️⃣ Convert CSV → JSONL
        
            if file.name.endswith(".csv"):
                decoded_file = file.read().decode("utf-8")
                io_string = io.StringIO(decoded_file)
                reader = list(csv.DictReader(io_string))
            else:
                return render(request, "products/bulk_upload.html", {
                    "form": form,
                    "error": "Only CSV or Excel files are supported."
                })

            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")

            for row in reader:
                data = {
                    "input": {
                        "title": row["title"],
                        "descriptionHtml": row["description"], 
                        "status": "ACTIVE",
                        "tags": [row["tag"]],                 
                    }
                }

                temp.write((json.dumps(data) + "\n").encode("utf-8"))

            temp.close()
            jsonl_path = temp.name

            # -----------------------------
            # 2️⃣ Create Staged Upload
            # -----------------------------
            graphql_url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

            headers = {
                "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
                "Content-Type": "application/json"
            }

            staged_query = """
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

            staged_response = requests.post(
                graphql_url,
                json={"query": staged_query},
                headers=headers
            )

            staged_data = staged_response.json()
            print("STAGED RESPONSE:", staged_data)

            target = staged_data["data"]["stagedUploadsCreate"]["stagedTargets"][0]

            # -----------------------------
            # 3️⃣ Upload JSONL to Google Storage
            # -----------------------------
            upload_url = target["url"]
            params = {p["name"]: p["value"] for p in target["parameters"]}

            with open(jsonl_path, "rb") as f:
                files = {"file": f}
                upload_response = requests.post(upload_url, data=params, files=files)

            print("Upload status:", upload_response.status_code)

            if upload_response.status_code not in [200, 201, 204]:
                return render(request, "products/bulk_upload.html", {
                    "form": form,
                    "error": "File upload failed."
                })

            # -----------------------------
            # 4️⃣ Extract CORRECT staged path (IMPORTANT FIX)
            # -----------------------------
            staged_path = None
            for param in target["parameters"]:
                if param["name"] == "key":
                    staged_path = param["value"]
                    break

            print("Correct staged path:", staged_path)

            # -----------------------------
            # 5️⃣ Run Bulk Operation
            # -----------------------------
            bulk_mutation = f"""
            mutation {{
              bulkOperationRunMutation(
                mutation: \"\"\"
                mutation productCreate($input: ProductCreateInput!) {{
                  productCreate(product: $input) {{
                    product {{
                      id
                    }}
                    userErrors {{
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
                  message
                }}
              }}
            }}
            """

            bulk_response = requests.post(
                graphql_url,
                json={"query": bulk_mutation},
                headers=headers
            )

            print("🔥 BULK RUN RESPONSE:", bulk_response.json())

            return redirect("staff_panel")

    else:
        form = CSVUploadForm()

    return render(request, "products/bulk_upload.html", {"form": form})

@login_required
def staff_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "staff/products.html", {"products": products})


import requests
from django.conf import settings
from django.shortcuts import redirect
from products.models import Product


def sync_shopify_products(request):

    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/products.json?limit=250"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN
    }

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()

        print("PRODUCT COUNT:", len(data.get("products", [])))

        for product in data.get("products", []):

            for variant in product.get("variants", []):

                Product.objects.update_or_create(
                    shopify_variant_id=variant["id"],
                    defaults={

                        # 🔑 IDs
                        "shopify_product_id": f"gid://shopify/Product/{product['id']}",

                        # 🧾 Basic Info
                        "title": product.get("title"),
                        "description": product.get("body_html"),

                        # 💰 Pricing
                        "price": float(variant.get("price", 0)),
                        "compare_price": float(variant.get("compare_at_price") or 0),

                        # 🏷️ Classification
                        "collection": product.get("product_type") or "General",
                        "tags": product.get("tags"),

                        # 💎 Jewelry fields (optional mapping)
                        "jewelry_type": product.get("product_type"),
                        "metal_type": None,
                        "stone_type": None,

                        # ⚖️ Weight
                        "weight": variant.get("weight") or 0,

                        # 📦 Inventory
                        "sku": variant.get("sku"),
                        "barcode": variant.get("barcode"),
                        "quantity": variant.get("inventory_quantity", 0),

                        # 🔧 Raw backup (VERY IMPORTANT)
                        "raw_data": product,
                    }
                )

                print(f"✅ Synced: {product['title']} (Variant: {variant['id']})")

        link_header = response.headers.get("Link")

        if link_header and 'rel="next"' in link_header:
            url = link_header.split(";")[0].strip("<> ")
        else:
            url = None

    print("🚀 Shopify sync completed")

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


@login_required
def delete_product(request, pk):
    product = Product.objects.get(pk=pk)

    if request.method == "POST":
        delete_product_shopify(product)  # 🔥 Delete in Shopify first
        product.delete()                 # Then delete locally

        return redirect("staff_products")

    return render(request, "staff/delete_product.html", {"product": product})


def update_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    product_id = product.shopify_product_id

    # 🔧 Ensure price is valid
    price = float(product.price or 0)

    # Update title
    mutation = f"""
    mutation {{
      productUpdate(input: {{
        id: "{product_id}",
        title: "{product.title}"
      }}) {{
        userErrors {{
          message
        }}
      }}
    }}
    """
    requests.post(url, json={"query": mutation}, headers=headers)

    # Update price
    price_mutation = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{product_id}",
        variants: [{{
            id: "{product.shopify_variant_id}",
            price: "{price}"
        }}]
      ) {{
        userErrors {{
          message
        }}
      }}
    }}
    """
    requests.post(url, json={"query": price_mutation}, headers=headers)

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

import json
import tempfile

def generate_jsonl_from_csv(file):
    decoded_file = file.read().decode("utf-8")
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")

    for row in reader:
        data = {
            "input": {
                "title": row["title"],
                "descriptionHtml": row["description"],
                "variants": [
                    {
                        "price": row["price"]
                    }
                ]
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
        mutation productCreate($input: ProductCreateInput!) {{
          productCreate(product: $input) {{
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


#Receives Shopify webhook↓Extracts product data !Updates Django DB
@csrf_exempt
def shopify_product_webhook(request):

    if request.method == "POST":
        data = json.loads(request.body)

        for variant in data.get("variants", []):

            Product.objects.update_or_create(
                shopify_variant_id=variant["id"],
                defaults={
                    "shopify_product_id": f"gid://shopify/Product/{data['id']}",
                    "title": data.get("title"),
                    "description": data.get("body_html"),

                    "price": float(variant.get("price", 0)),
                    "compare_price": float(variant.get("compare_at_price") or 0),

                    "collection": data.get("product_type"),
                    "tags": data.get("tags"),

                    "sku": variant.get("sku"),
                    "barcode": variant.get("barcode"),
                    "weight": variant.get("weight"),
                    "quantity": variant.get("inventory_quantity", 0),

                    "raw_data": data
                }
            )

        return HttpResponse(status=200)

    return HttpResponse(status=405)






