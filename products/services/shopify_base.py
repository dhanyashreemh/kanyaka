import requests
from django.conf import settings

GRAPHQL_URL = f"https://{settings.SHOPIFY_STORE}/admin/api/2025-10/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
}

def shopify_request(query, variables=None):
    return requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=HEADERS,
    ).json()