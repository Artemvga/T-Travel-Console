from django.db import models


class Carrier(models.Model):
    class TransportType(models.TextChoices):
        PLANE = "plane", "Plane"
        TRAIN = "train", "Train"
        BUS = "bus", "Bus"
        ELECTRIC_TRAIN = "electric_train", "Electric train"

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=160)
    transport_type = models.CharField(max_length=24, choices=TransportType.choices)
    reference_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
