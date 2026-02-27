from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("update-rate/", views.update_rate, name="update_rate"),
]