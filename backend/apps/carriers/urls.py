from django.urls import path

from .views import CarrierListAPIView

urlpatterns = [
    path("carriers/", CarrierListAPIView.as_view(), name="carrier-list"),
]
