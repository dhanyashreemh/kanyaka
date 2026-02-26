from django.urls import path
from .views import shopify_webhook

urlpatterns = [
    path("webhook/shopify/", shopify_webhook, name="shopify_webhook"),
]