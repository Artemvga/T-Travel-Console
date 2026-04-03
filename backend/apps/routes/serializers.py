from datetime import time

from rest_framework import serializers


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
