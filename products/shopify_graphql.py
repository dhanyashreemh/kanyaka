import requests
from django.conf import settings
import json
import os


def create_products_sync(products):

    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2026-01/graphql.json"

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
    }

    mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    results = []

    for product in products:
        variables = {
            "input": {
                "title": product["title"],
                "descriptionHtml": product.get("description", ""),
                "vendor": product.get("vendor", "Default Vendor"),
                "productType": product.get("type", "General"),
            }
        }

        response = requests.post(
            url,
            json={"query": mutation, "variables": variables},
            headers=headers,
        )

        results.append(response.json())

    return results



#creating bulk products

def create_products_bulk(products):
    url = f"https://{settings.SHOPIFY_STORE}/admin/api/2026-01/graphql.json"

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
    }

    # Step 1: Create JSONL
    file_path = "products.jsonl"

    with open(file_path, "w") as f:
        for product in products:
            line = {
                "input": {
                    "title": product["title"],
                    "descriptionHtml": product.get("description", ""),
                    "vendor": product.get("vendor", "Default Vendor"),
                    "productType": product.get("type", "General"),
                }
            }
            f.write(json.dumps(line) + "\n")

    # Step 2: Get staged upload
    staged_query = """
    mutation {
      stagedUploadsCreate(input: {
        resource: BULK_MUTATION_VARIABLES,
        filename: "products.jsonl",
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

    staged_response = requests.post(url, json={"query": staged_query}, headers=headers)
    staged_data = staged_response.json()

    target = staged_data["data"]["stagedUploadsCreate"]["stagedTargets"][0]

    # Step 3: Upload file
    files = {'file': open(file_path, 'rb')}
    data = {p["name"]: p["value"] for p in target["parameters"]}

    requests.post(target["url"], data=data, files=files)

    # Step 4: Run bulk mutation
    bulk_mutation = f"""
    mutation {{
      bulkOperationRunMutation(
        mutation: \"\"\"
          mutation productCreate($input: ProductInput!) {{
            productCreate(input: $input) {{
              product {{ id }}
              userErrors {{ message }}
            }}
          }}
        \"\"\",
        stagedUploadPath: "{target['resourceUrl']}"
      ) {{
        bulkOperation {{
          id
          status
        }}
      }}
    }}
    """

    bulk_response = requests.post(url, json={"query": bulk_mutation}, headers=headers)

    return bulk_response.json()


def bulk_create_products(products):
    if len(products) < 50:
        return create_products_sync(products)
    else:
        return create_products_bulk(products)