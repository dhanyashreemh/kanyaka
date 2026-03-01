import requests
from django.conf import settings


def bulk_create_products(products):

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