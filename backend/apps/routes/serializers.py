from datetime import time

from rest_framework import serializers

from .models import RouteFavorite


class RouteBuildRequestSerializer(serializers.Serializer):
    from_city = serializers.CharField()
    to_city = serializers.CharField()
    via_city = serializers.CharField(required=False, allow_blank=True)
    departure_date = serializers.DateField()
    departure_time = serializers.TimeField(required=False, default=time(0, 0))
    priority = serializers.ChoiceField(
        choices=("optimal", "cheapest", "fastest"),
        default="optimal",
        required=False,
    )
    preferred_carriers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    preferred_transport_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    direct_only = serializers.BooleanField(required=False, default=False)
    allow_transfers = serializers.BooleanField(required=False, default=True)
    max_transfers = serializers.IntegerField(required=False, min_value=0, max_value=5, default=2)
    show_alternatives = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs["from_city"].strip().lower() == attrs["to_city"].strip().lower():
            raise serializers.ValidationError(
                "Города отправления и назначения должны различаться."
            )

        via_city = (attrs.get("via_city") or "").strip()
        attrs["via_city"] = via_city

        if via_city:
            normalized_via = via_city.lower()
            if normalized_via == attrs["from_city"].strip().lower():
                raise serializers.ValidationError(
                    "Транзитный город должен отличаться от города отправления."
                )
            if normalized_via == attrs["to_city"].strip().lower():
                raise serializers.ValidationError(
                    "Транзитный город должен отличаться от города прибытия."
                )

        preferred_transport_types = attrs.get("preferred_transport_types") or []
        normalized_transport = [
            item for item in preferred_transport_types if item != "multimodal"
        ]
        attrs["preferred_transport_types"] = normalized_transport

        if attrs.get("direct_only"):
            if via_city:
                raise serializers.ValidationError(
                    "Нельзя требовать транзитный город и одновременно искать только прямые маршруты."
                )
            attrs["allow_transfers"] = False
            attrs["max_transfers"] = 0

        if via_city and not attrs.get("allow_transfers", True):
            raise serializers.ValidationError(
                "Для маршрута через транзитный город нужно разрешить пересадки."
            )

        if via_city and attrs.get("max_transfers", 0) < 1:
            raise serializers.ValidationError(
                "Для транзитного маршрута нужен минимум один допустимый переход."
            )

        return attrs


class RouteFavoriteWriteSerializer(serializers.Serializer):
    route_title = serializers.CharField(required=False, allow_blank=True, max_length=120)
    query = serializers.DictField()
    route_data = serializers.DictField()

    def validate_route_data(self, value):
        if not value.get("segments"):
            raise serializers.ValidationError("Нечего сохранять: маршрут пустой.")
        if not value.get("waypoints"):
            raise serializers.ValidationError("Маршрут должен содержать точки пути.")
        return value

    def validate_query(self, value):
        required_fields = ("from_city_slug", "to_city_slug", "departure_date", "departure_time", "priority")
        missing = [field for field in required_fields if not value.get(field)]
        if missing:
            raise serializers.ValidationError(
                f"Недостаточно данных для сохранения маршрута: {', '.join(missing)}."
            )
        return value


class RouteFavoriteSerializer(serializers.ModelSerializer):
    from_city = serializers.SerializerMethodField()
    via_city = serializers.SerializerMethodField()
    to_city = serializers.SerializerMethodField()
    query = serializers.SerializerMethodField()
    route = serializers.JSONField(source="route_data")

    class Meta:
        model = RouteFavorite
        fields = (
            "id",
            "route_title",
            "from_city",
            "via_city",
            "to_city",
            "departure_at",
            "priority_mode",
            "created_at",
            "query",
            "route",
        )

    @staticmethod
    def _serialize_city(city):
        if not city:
            return None
        return {
            "name": city.name,
            "slug": city.slug,
            "region": city.region,
        }

    def get_from_city(self, obj):
        return self._serialize_city(obj.from_city)

    def get_via_city(self, obj):
        return self._serialize_city(obj.via_city)

    def get_to_city(self, obj):
        return self._serialize_city(obj.to_city)

    def get_query(self, obj):
        return {
            "from_city": obj.from_city.name if obj.from_city else None,
            "from_city_slug": obj.from_city.slug if obj.from_city else None,
            "via_city": obj.via_city.name if obj.via_city else None,
            "via_city_slug": obj.via_city.slug if obj.via_city else None,
            "to_city": obj.to_city.name if obj.to_city else None,
            "to_city_slug": obj.to_city.slug if obj.to_city else None,
            "departure_date": obj.departure_at.date().isoformat(),
            "departure_time": obj.departure_at.time().isoformat(timespec="minutes"),
            "priority": obj.priority_mode,
        }
