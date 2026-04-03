from rest_framework import serializers

from .models import Carrier


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = (
            "id",
            "code",
            "name",
            "transport_type",
            "reference_url",
            "metadata",
            "is_active",
        )
