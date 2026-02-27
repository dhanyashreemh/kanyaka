from django.urls import path
from .views import gold_rate_api, test_api

urlpatterns = [
    path("gold-rate/", gold_rate_api),
    path("test/", test_api),
]