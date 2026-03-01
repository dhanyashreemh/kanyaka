from django.urls import path
from .views import create_bulk_products

urlpatterns = [
    path("bulk-create/", create_bulk_products),
]