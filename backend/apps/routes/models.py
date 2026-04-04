from django.conf import settings
from django.db import models


class RouteSearchLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="route_search_logs",
        null=True,
        blank=True,
    )
    from_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="logged_from_searches",
        null=True,
        blank=True,
    )
    via_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="logged_via_searches",
        null=True,
        blank=True,
    )
    to_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="logged_to_searches",
        null=True,
        blank=True,
    )
    departure_at = models.DateTimeField()
    priority_mode = models.CharField(max_length=24, default="optimal")
    selected_transport = models.JSONField(default=list, blank=True)
    selected_carriers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return (
            f"{self.user or 'guest'}: "
            f"{self.from_city} -> {self.to_city} ({self.departure_at:%Y-%m-%d %H:%M})"
        )


class RouteFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_routes",
    )
    from_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="favorite_from_routes",
        null=True,
        blank=True,
    )
    via_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="favorite_via_routes",
        null=True,
        blank=True,
    )
    to_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        related_name="favorite_to_routes",
        null=True,
        blank=True,
    )
    departure_at = models.DateTimeField()
    priority_mode = models.CharField(max_length=24, default="optimal")
    route_title = models.CharField(max_length=120, blank=True, default="")
    route_signature = models.CharField(max_length=1024)
    route_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "route_signature", "departure_at"),
                name="unique_user_route_favorite",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.route_title or self.route_signature}"
