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



class ProductForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea, required=False)
    price = forms.DecimalField(max_digits=10, decimal_places=2)
    compare_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    collection = forms.CharField(required=False)
    jewelry_type = forms.CharField(required=False)
    metal_type = forms.CharField(required=False)
    stone_type = forms.CharField(required=False)
    purity = forms.CharField(required=False)
    occasion = forms.CharField(required=False)
    weight = forms.DecimalField(required=False)
    quantity = forms.IntegerField()
    sku = forms.CharField(required=False)


class CSVUploadForm(forms.Form):
    file = forms.FileField()


#Get Online Store Publication ID
def get_online_store_publication_id():
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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

    for pub in data["data"]["publications"]["edges"]:
        if pub["node"]["name"] == "Online Store":
            return pub["node"]["id"]

    return None



#publishes the product to Online Store.
def publish_product_to_online_store(product_id):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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
def create_product_shopify(title,description,price,collection=None,compare_price=None,jewelry_type=None,metal_type=None,stone_type=None,purity=None,occasion=None,weight=None,quantity=0,sku=None,tags=None,image_url=None):

    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    # Convert tags string → list
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # -------------------------
    # Create Product
    # -------------------------

    create_query = """
    mutation productCreate($input: ProductInput!) {
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
            "descriptionHtml": description,
            "status": "ACTIVE",
            "tags": tag_list
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json={"query": create_query, "variables": variables}
    )

    data = response.json()
    print("PRODUCT CREATE RESPONSE:", data)

    product_data = data["data"]["productCreate"]["product"]
    product_id = product_data["id"]

    variant_data = product_data["variants"]["edges"][0]["node"]
    variant_id = variant_data["id"]

    # -------------------------
    # Update Price
    # -------------------------

    update_query = """
    mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants {
          id
          price
        }
        userErrors {
          message
        }
      }
    }
    """

    update_variables = {
        "productId": product_id,
        "variants": [
            {
                "id": variant_id,
                "price": str(price)
            }
        ]
    }

    requests.post(
        url,
        headers=headers,
        json={"query": update_query, "variables": update_variables}
    )

    # -------------------------
    # Add Image (if provided)
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
            "media": [
                {
                    "mediaContentType": "IMAGE",
                    "originalSource": image_url
                }
            ]
        }

        requests.post(
            url,
            headers=headers,
            json={"query": image_query, "variables": image_variables}
        )

    # -------------------------
    # Publish to Store
    # -------------------------

    publish_product_to_online_store(product_id)

    # -------------------------
    # Save to Database
    # -------------------------

    Product.objects.update_or_create(
      shopify_product_id=product_id,
      defaults={
          "title": title,
          "description": description,
          "price": price,
          "compare_price": compare_price,
          "collection": collection,
          "jewelry_type": jewelry_type,
          "metal_type": metal_type,
          "stone_type": stone_type,
          "purity": purity,
          "occasion": occasion,
          "weight": weight,
          "quantity": quantity,
          "sku": sku
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

            data = form.cleaned_data

            create_product_shopify(
                title=data["title"],
                description=data["description"],
                price=data["price"],
                collection=data["collection"],
                compare_price=data["compare_price"],
                jewelry_type=data["jewelry_type"],
                metal_type=data["metal_type"],
                stone_type=data["stone_type"],
                purity=data["purity"],
                occasion=data["occasion"],
                weight=data["weight"],
                quantity=data["quantity"],
                sku=data["sku"],
            )

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

            # -----------------------------
            # 1️⃣ Convert CSV → JSONL
            # -----------------------------
            # -----------------------------

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
            graphql_url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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
                mutation productCreate($input: ProductInput!) {{
                  productCreate(input: $input) {{
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


def sync_shopify_products(request):

    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/products.json?limit=250"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN
    }

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()

        for product in data.get("products", []):

            shopify_product_id = f"gid://shopify/Product/{product['id']}"

            price = 0
            if product.get("variants"):
                price = product["variants"][0]["price"]

            Product.objects.update_or_create(
                shopify_product_id=shopify_product_id,
                defaults={
                    "title": product["title"],
                    "price": price,
                    "raw_data": product,
                }
            )

        # Shopify pagination
        link_header = response.headers.get("Link")

        if link_header and 'rel="next"' in link_header:
            url = link_header.split(";")[0].strip("<> ")
        else:
            url = None

    return redirect("staff_products")



@login_required
def edit_product(request, pk):
    product = Product.objects.get(pk=pk)

    if request.method == "POST":
        product.title = request.POST.get("title")
        product.price = request.POST.get("price")

        update_product_shopify(product)  # 🔥 Update Shopify first
        product.save()                   # Then save locally

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


import requests

def update_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }



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

    price_mutation = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{product_id}",
        variants: [{{
          id: "{variant_id}",
          price: "{product.price}"
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
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    mutation = f"""
    mutation {{
      bulkOperationRunMutation(
        mutation: \"\"\"
        mutation productCreate($input: ProductInput!) {{
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
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

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

        shopify_product_id = f"gid://shopify/Product/{data['id']}"

        price = 0
        if data.get("variants"):
            price = data["variants"][0]["price"]

        Product.objects.update_or_create(
            shopify_product_id=shopify_product_id,
            defaults={
                "title": data["title"],
                "price": price,
            }
        )

        return HttpResponse(status=200)

    return HttpResponse(status=405)






