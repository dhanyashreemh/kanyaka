from django.urls import path

from api import views
from .views import bulk_status, create_bulk_products, upload_products

urlpatterns = [
    path("manual-upload/", views.manual_product_upload, name="manual_product_upload"),
    path("bulk-upload/", views.bulk_product_upload, name="bulk_product_upload"),
]