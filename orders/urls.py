from django.urls import path
from .views import shopify_webhook

urlpatterns = [
    path("order/", shopify_webhook, name="shopify_webhook"),
]