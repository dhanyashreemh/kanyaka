import hmac
import hashlib
import base64
from django.conf import settings

def verify_webhook(request):
    received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")

    # 🔥 FIX 1: handle missing header
    if not received_hmac:
        return False

    secret = settings.SHOPIFY_WEBHOOK_SECRET

    # 🔥 FIX 2: handle missing secret (extra safety)
    if not secret:
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).digest()

    calculated_hmac = base64.b64encode(digest).decode()

    # 🔥 FIX 3: always compare strings
    return hmac.compare_digest(str(received_hmac), str(calculated_hmac))