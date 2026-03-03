import json
import requests
from .shopify_base import GRAPHQL_URL, HEADERS


def create_jsonl(products):
    file_path = "bulk_products.jsonl"

    with open(file_path, "w") as f:
        for p in products:
            line = {
                "input": {
                    "title": p["title"],
                    "productType": p.get("type", "General"),
                    "status": "ACTIVE"
                }
            }
            f.write(json.dumps(line) + "\n")

    return file_path


def run_bulk_upload(products):

    # Step 1: Create JSONL
    file_path = create_jsonl(products)

    # Step 2: Get staged upload URL
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
        GRAPHQL_URL,
        json={"query": staged_query},
        headers=HEADERS
    ).json()

    target = staged_response["data"]["stagedUploadsCreate"]["stagedTargets"][0]

    # Step 3: Upload file
    with open(file_path, "rb") as f:
        files = {"file": f}
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

    bulk_response = requests.post(
        GRAPHQL_URL,
        json={"query": bulk_mutation},
        headers=HEADERS
    ).json()

    return bulk_response

def check_bulk_status():

    query = """
    {
      currentBulkOperation {
        id
        status
        errorCode
        url
      }
    }
    """

    response = requests.post(
        GRAPHQL_URL,
        json={"query": query},
        headers=HEADERS
    ).json()

    return response