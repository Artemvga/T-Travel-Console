from django.core.exceptions import ValidationError
from django.db import models


class Ticket(models.Model):
    class TransportType(models.TextChoices):
        PLANE = "plane", "Plane"
        TRAIN = "train", "Train"
        BUS = "bus", "Bus"
        ELECTRIC_TRAIN = "electric_train", "Electric train"

    external_id = models.CharField(max_length=128, unique=True)
    carrier = models.ForeignKey(
        "carriers.Carrier",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    from_city = models.ForeignKey(
        "cities.City",
        on_delete=models.CASCADE,
        related_name="tickets_from",
    )
    to_city = models.ForeignKey(
        "cities.City",
        on_delete=models.CASCADE,
        related_name="tickets_to",
    )
    transport_type = models.CharField(max_length=24, choices=TransportType.choices)
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    distance_km = models.PositiveIntegerField()
    is_direct = models.BooleanField(default=True)
    available_seats = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    generation_batch = models.CharField(max_length=96, blank=True, default="")
    route_signature = models.CharField(max_length=64, blank=True, default="")
    generation_meta = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("departure_datetime", "price")
        indexes = [
            models.Index(fields=("from_city", "departure_datetime", "is_active")),
            models.Index(
                fields=("from_city", "departure_datetime", "transport_type", "is_active")
            ),
            models.Index(fields=("from_city", "to_city", "departure_datetime")),
            models.Index(fields=("transport_type", "departure_datetime", "is_active")),
            models.Index(fields=("carrier", "departure_datetime")),
            models.Index(fields=("is_active", "departure_datetime")),
            models.Index(fields=("generation_batch", "departure_datetime")),
            models.Index(fields=("route_signature", "departure_datetime")),
            models.Index(
                fields=("from_city", "departure_datetime"),
                name="tickets_act_from_dep_idx",
                condition=models.Q(is_active=True, available_seats__gt=0),
            ),
            models.Index(
                fields=("from_city", "transport_type", "departure_datetime"),
                name="tickets_act_from_ttype_dep_idx",
                condition=models.Q(is_active=True, available_seats__gt=0),
            ),
            models.Index(
                fields=("from_city", "to_city", "departure_datetime"),
                name="tickets_act_from_to_dep_idx",
                condition=models.Q(is_active=True, available_seats__gt=0),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.external_id}: {self.from_city} -> {self.to_city}"

    def clean(self):
        if self.from_city_id == self.to_city_id:
            raise ValidationError("Origin and destination cities must differ.")
        if self.arrival_datetime <= self.departure_datetime:
            raise ValidationError("Arrival time must be after departure time.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
