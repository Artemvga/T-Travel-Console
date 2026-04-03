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
