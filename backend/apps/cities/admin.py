from django.contrib import admin

from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "region",
        "slug",
        "population",
        "latitude",
        "longitude",
        "has_airport",
        "has_train_station",
        "has_bus_station",
        "has_commuter_station",
    )
    list_filter = (
        "has_airport",
        "has_train_station",
        "has_bus_station",
        "has_commuter_station",
    )
    search_fields = ("name", "slug", "region")
    ordering = ("name",)
