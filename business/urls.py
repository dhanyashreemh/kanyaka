# urls.py
from django.urls import path
from . import views

urlpatterns = [
 
    path("staff/dashboard/", views.dashboard, name="dashboard"),
    path("staff/update-rate/", views.update_rate, name="update_rate"),
    path("api/gold-rate/", views.gold_rate_api, name="gold_rate_api"),
]