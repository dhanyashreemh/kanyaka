from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # API
    path("api/", include("api.urls")),

    # Webhooks
    path("webhook/", include("orders.urls")),

    # Products
    path("products/", include("products.urls")),

    # Staff Auth
    path("staff/login/", auth_views.LoginView.as_view(template_name="staff/login.html"), name="login"),
    path("staff/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Business dashboard
    path("", include("business.urls")),

    # Root redirect
    path("", RedirectView.as_view(url="/staff/login/", permanent=False)),
]