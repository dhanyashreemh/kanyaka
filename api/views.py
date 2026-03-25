from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from business.services import get_gold_rate
from business.shopify_service import get_shopify_products
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def gold_rate_api(request):

    data = get_gold_rate()

    if not data:
        logger.warning("No gold rate found in DB")
        return Response({"error": "No rate available"}, status=404)

    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def shopify_products_api(request):

    result = get_shopify_products()

    if isinstance(result, tuple):
        data, status = result
        return Response(data, status=status)

    return Response(result)