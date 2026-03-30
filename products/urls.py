from django.urls import path
from . import views

urlpatterns = [

    # 🔹 Product CRUD (staff)
    path("staff/products/", views.staff_products, name="staff_products"),
    path("staff/products/<int:pk>/", views.product_detail, name="product_detail"),
    path("staff/products/<int:pk>/edit/", views.edit_product, name="edit_product"),
    path("staff/products/<int:pk>/delete/", views.delete_product, name="delete_product"),

    # 🔹 Uploads
    path("products/manual-upload/", views.manual_product_upload, name="manual_product_upload"),
    path("products/bulk-upload/", views.bulk_product_upload, name="bulk_product_upload"),
    path("products/bulk-status/", views.bulk_status_view, name="bulk_status"),

    # 🔹 Sync
    path("products/sync/", views.sync_shopify_products, name="sync_products"),

    # 🔹 Webhooks (external)
    path("product-create/", views.shopify_product_webhook),
]