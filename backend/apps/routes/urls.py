from django.urls import path

from .views import (
    DatasetStatsAPIView,
    FavoriteRouteDeleteAPIView,
    FavoriteRouteListCreateAPIView,
    HealthCheckAPIView,
    RouteBuildAPIView,
)

urlpatterns = [
    path("routes/build/", RouteBuildAPIView.as_view(), name="route-build"),
    path("routes/favorites/", FavoriteRouteListCreateAPIView.as_view(), name="route-favorites"),
    path(
        "routes/favorites/<int:pk>/",
        FavoriteRouteDeleteAPIView.as_view(),
        name="route-favorite-delete",
    ),
    path("health/", HealthCheckAPIView.as_view(), name="health-check"),
    path("stats/", DatasetStatsAPIView.as_view(), name="dataset-stats"),
]
