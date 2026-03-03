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


    if not data.get("data"):
        return None

    edges = data["data"]["productVariants"]["edges"]

    if edges:
        return edges[0]["node"]

    return None


def create_product(product):

    # Step 1: Create product
    mutation = f"""
    mutation {{
      productCreate(product: {{
        title: "{product['title']}",
        status: ACTIVE
      }}) {{
        product {{
          id
          variants(first: 1) {{
            edges {{
              node {{
                id
                inventoryItem {{ id }}
              }}
            }}
          }}
        }}
        userErrors {{ message }}
      }}
    }}
    """

    data = shopify_request(mutation)

    if data.get("errors"):
        return data

    product_data = data["data"]["productCreate"]["product"]
    variant_node = product_data["variants"]["edges"][0]["node"]

    product_id = product_data["id"]
    variant_id = variant_node["id"]
    inventory_item_id = variant_node["inventoryItem"]["id"]

    # Step 2: Update variant price + sku
    update_variant = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{product_id}",
        variants: [{{
          id: "{variant_id}",
          price: "{product['price']}",
          sku: "{product['sku']}"
        }}]
      ) {{
        userErrors {{ message }}
      }}
    }}
    """

    shopify_request(update_variant)

    return data

def update_product(existing_variant, product):

    mutation = f"""
    mutation {{
      productVariantsBulkUpdate(
        productId: "{existing_variant['product']['id']}",
        variants: [{{
          id: "{existing_variant['id']}",
          price: "{product['price']}"
        }}]
      ) {{
        userErrors {{ message }}
      }}
    }}
    """

    return shopify_request(mutation)

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