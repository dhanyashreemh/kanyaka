import hmac
import hashlib
import base64
from django.conf import settings

def verify_webhook(request):
    received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")

    digest = hmac.new(
        settings.SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).digest()

    calculated_hmac = base64.b64encode(digest).decode()

    return hmac.compare_digest(received_hmac, calculated_hmac)