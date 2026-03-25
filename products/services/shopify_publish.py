import requests
from django.conf import settings

def publish_product_to_online_store(product_id):
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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


#Get Online Store Publication ID
def get_online_store_publication_id():
    url = f"https://{settings.SHOPIFY_STORE}.myshopify.com/admin/api/2024-10/graphql.json"

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

