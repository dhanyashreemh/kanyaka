from .shopify_sync import sync_products
from .shopify_bulk import run_bulk_upload

def manage_products(products):

    if len(products) > 1000:
        return run_bulk_upload(products)

    return sync_products(products)