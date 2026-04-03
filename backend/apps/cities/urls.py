from django.urls import path

from .views import CityDetailAPIView, CityListAPIView, CitySearchAPIView

urlpatterns = [
    path("cities/", CityListAPIView.as_view(), name="city-list"),
    path("cities/search/", CitySearchAPIView.as_view(), name="city-search"),
    path("cities/<slug:slug>/", CityDetailAPIView.as_view(), name="city-detail"),
]
