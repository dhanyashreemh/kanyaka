from django.urls import path
from .views import gold_rate_api, shopify_products_api

urlpatterns = [
    path("gold-rate/", gold_rate_api),
    path('shopify-products/', shopify_products_api),
]