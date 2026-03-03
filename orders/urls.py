from django.urls import path

from business.views import staff_orders
from .views import shopify_webhook

urlpatterns = [
    path("order/", shopify_webhook, name="shopify_webhook"),
    path("staff/orders/", staff_orders, name="staff_orders"),
]