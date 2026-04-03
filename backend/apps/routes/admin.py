from django.contrib import admin

from .models import RouteSearchLog


@admin.register(RouteSearchLog)
class RouteSearchLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "from_city",
        "via_city",
        "to_city",
        "departure_at",
        "priority_mode",
        "created_at",
    )
    list_filter = ("priority_mode", "departure_at")
    search_fields = ("user__username", "from_city__name", "via_city__name", "to_city__name")
    autocomplete_fields = ("from_city", "via_city", "to_city")
    ordering = ("-created_at",)
