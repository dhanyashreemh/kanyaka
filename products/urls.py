from django.urls import path

from . import views


urlpatterns = [
    path("manual-upload/", views.manual_product_upload, name="manual_product_upload"),
    path("bulk-upload/", views.bulk_product_upload, name="bulk_product_upload"),
]