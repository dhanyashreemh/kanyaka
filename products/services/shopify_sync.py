# products/services/shopify_sync.py

from django.conf import settings
from .shopify_base import shopify_request


def find_variant_by_sku(sku):
    query = f"""
    {{
      productVariants(first: 1, query: "sku:{sku}") {{
        edges {{
          node {{
            id
            product {{ id }}
          }}
        }}
      }}
    }}
    """

    data = shopify_request(query)

    print("SKU Search Response:", data)  # DEBUG LINE

    if not data.get("data"):
        return None

    edges = data["data"]["productVariants"]["edges"]

    if edges:
        return edges[0]["node"]

    return None


def create_product(product):
    mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product { id }
        userErrors { message }
      }
    }
    """

    variables = {
        "input": {
            "title": product["title"],
            "status": "ACTIVE",
            "productType": product.get("type", "General"),
            "variants": [
                {
                    "sku": product["sku"],
                    "price": str(product["price"]),
                    "weight": float(product.get("weight", 0)),
                    "weightUnit": "GRAMS"
                }
            ]
        }
    }

    return shopify_request(mutation, variables)


def update_product(existing_variant, product):
    mutation = """
    mutation productVariantUpdate($input: ProductVariantInput!) {
      productVariantUpdate(input: $input) {
        productVariant { id }
        userErrors { message }
      }
    }
    """

    variables = {
        "input": {
            "id": existing_variant["id"],
            "price": str(product["price"]),
        }
    }

    return shopify_request(mutation, variables)


def sync_products(products):
    results = {"created": 0, "updated": 0, "errors": []}

    for product in products:
        existing = find_variant_by_sku(product["sku"])

        if existing:
            response = update_product(existing, product)
            results["updated"] += 1
        else:
            response = create_product(product)
            results["created"] += 1
 
        errors = response.get("data", {}).get("productCreate", {}).get("userErrors", [])
        if errors:
            results["errors"].append(errors)

    return results