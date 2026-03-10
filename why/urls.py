from django.urls import path
from .views import why_view

urlpatterns = [
    path("", why_view, name="why"),
]