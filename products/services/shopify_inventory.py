import requests
from django.conf import settings

def update_inventory_item(inventory_item_id, sku=None):

    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    mutation = """
    mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
      inventoryItemUpdate(id: $id, input: $input) {
        inventoryItem {
          id
          sku
        }
        userErrors {
          message
        }
      }
    }
    """

    variables = {
        "id": inventory_item_id,
        "input": {
            "sku": sku or ""
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json={"query": mutation, "variables": variables}
    )

    print("✅ SKU UPDATE RESPONSE:", response.json())