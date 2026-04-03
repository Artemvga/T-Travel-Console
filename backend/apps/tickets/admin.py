from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "carrier",
        "transport_type",
        "from_city",
        "to_city",
        "departure_datetime",
        "duration_minutes",
        "price",
        "available_seats",
        "is_active",
    )
    list_filter = ("transport_type", "is_active", "carrier")
    search_fields = (
        "external_id",
        "from_city__name",
        "to_city__name",
        "carrier__name",
    )
    autocomplete_fields = ("carrier", "from_city", "to_city")
    ordering = ("-departure_datetime",)
