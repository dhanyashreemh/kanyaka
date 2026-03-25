import requests
import os
from django.conf import settings
from products.services.shopify_publish import publish_product_to_online_store
from products.services.metafields import update_product_metafields
from products.services.shopify_inventory import update_inventory_item

# SHOPIFY GRAPHQL FUNCTION

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
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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
            sku=sku
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




def update_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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



def delete_product_shopify(product):
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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



