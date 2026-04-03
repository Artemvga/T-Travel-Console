from django.contrib import admin

from .models import Carrier


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "transport_type", "reference_url", "is_active")
    list_filter = ("transport_type", "is_active")
    search_fields = ("name", "code")
    ordering = ("name",)
