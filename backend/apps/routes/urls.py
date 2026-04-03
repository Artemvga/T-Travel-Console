from django.urls import path

from .views import DatasetStatsAPIView, HealthCheckAPIView, RouteBuildAPIView

urlpatterns = [
    path("routes/build/", RouteBuildAPIView.as_view(), name="route-build"),
    path("health/", HealthCheckAPIView.as_view(), name="health-check"),
    path("stats/", DatasetStatsAPIView.as_view(), name="dataset-stats"),
]
