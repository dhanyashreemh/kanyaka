"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public API
    path("api/", include("api.urls")),

    # Webhooks
    path("webhooks/", include("orders.urls")),

    # Staff authentication
    path(
        "staff/login/",
        auth_views.LoginView.as_view(template_name="staff/login.html"),
        name="login",
    ),
    path(
        "staff/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    # Staff dashboard + business routes
    path("staff/", include("business.urls")),

    # Root redirect
    path("", RedirectView.as_view(url="/staff/login/", permanent=False)),
]