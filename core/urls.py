from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from core import settings
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Webhook under explicit prefix
    path("webhook/", include("orders.urls")),

    # API
    path("api/", include("api.urls")),

    # Products
    path("products/", include("products.urls")),

    # Staff Auth
    path("staff/login/", auth_views.LoginView.as_view(template_name="staff/login.html"), name="login"),
    path("staff/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Business routes
    path("", include("business.urls")),

    # Default redirect
    path("", RedirectView.as_view(url="/staff/login/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])