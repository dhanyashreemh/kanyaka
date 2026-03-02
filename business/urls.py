# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("staff-panel/", views.staff_panel, name="staff_panel"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("update-rate/", views.update_rate, name="update_rate"),
]