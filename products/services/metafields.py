import requests
from django.conf import settings

def get_shopify_metafields(product_gid):
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"
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


def update_product_metafields(product):
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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
    

