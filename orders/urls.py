from django.urls import path
from .views import shopify_webhook

urlpatterns = [
    path("shopify/", shopify_webhook, name="shopify_webhook"),
]