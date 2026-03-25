from django.urls import path
from . import views

urlpatterns = [

    # Staff main
    path("staff/", views.staff_panel, name="staff_panel"),
    path("staff/dashboard/", views.dashboard, name="dashboard"),

    # Staff actions
    path("staff/update-rate/", views.update_rate, name="update_rate"),

    # Staff resources
    path("staff/orders/", views.staff_orders, name="staff_orders"),
    path("staff/products/", views.staff_products, name="staff_products"),
]