from rest_framework import serializers

from .models import City


class CityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "slug",
            "region",
            "population",
            "latitude",
            "longitude",
            "has_airport",
            "has_train_station",
            "has_bus_station",
            "has_commuter_station",
        )


class CitySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "slug", "region", "population", "latitude", "longitude")


class CityDetailSerializer(serializers.ModelSerializer):
    available_transports = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    available_directions_count = serializers.IntegerField(read_only=True)
    active_tickets_count = serializers.IntegerField(read_only=True)
    city_energy = serializers.IntegerField(read_only=True)
    popular_destinations = serializers.ListField(read_only=True)
    tickets_by_transport = serializers.ListField(read_only=True)

    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "slug",
            "region",
            "population",
            "latitude",
            "longitude",
            "has_airport",
            "has_train_station",
            "has_bus_station",
            "has_commuter_station",
            "available_transports",
            "active_tickets_count",
            "available_directions_count",
            "tickets_by_transport",
            "city_energy",
            "popular_destinations",
        )
