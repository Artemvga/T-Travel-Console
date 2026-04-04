from django.db import models
from django.utils.text import slugify


class City(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=160, unique=True)
    region = models.CharField(max_length=128, blank=True, default="")
    population = models.PositiveIntegerField(default=0)
    latitude = models.FloatField()
    longitude = models.FloatField()
    has_airport = models.BooleanField(default=False)
    has_international_airport = models.BooleanField(default=False)
    has_train_station = models.BooleanField(default=False)
    has_bus_station = models.BooleanField(default=False)
    has_commuter_station = models.BooleanField(default=False)
    is_rail_hub = models.BooleanField(default=False)
    is_bus_hub = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def available_transports(self) -> list[str]:
        transports = []
        if self.has_bus_station:
            transports.append("bus")
        if self.has_train_station:
            transports.append("train")
        if self.has_airport:
            transports.append("plane")
        if self.has_commuter_station:
            transports.append("electric_train")
        return transports
