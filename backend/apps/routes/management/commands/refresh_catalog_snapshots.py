import json
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Case, CharField, Count, F, IntegerField, Q, When

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.routes.models import RouteSearchLog
from apps.routes.views import TRANSPORT_LABELS
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Build JSON snapshots for heavy catalog pages."

    def handle(self, *args, **options):
        cache_dir = Path(settings.DATA_DIR) / "cache"
        city_dir = cache_dir / "city_details"
        city_dir.mkdir(parents=True, exist_ok=True)

        active_tickets = Ticket.objects.filter(is_active=True)

        transport_rows = (
            active_tickets.values("transport_type")
            .annotate(total=Count("id"))
            .order_by("transport_type")
        )
        transport_counts = {
            row["transport_type"]: row["total"] for row in transport_rows
        }

        carrier_rows = (
            active_tickets.values("transport_type", "carrier__name")
            .annotate(total=Count("id"))
            .order_by("transport_type", "-total", "carrier__name")
        )
        carriers_by_transport = defaultdict(list)
        for row in carrier_rows:
            carriers_by_transport[row["transport_type"]].append(
                {
                    "name": row["carrier__name"],
                    "tickets_count": row["total"],
                }
            )

        popular_direction_rows = (
            active_tickets.values("transport_type", "from_city__name", "to_city__name")
            .annotate(total=Count("id"))
            .order_by("transport_type", "-total", "from_city__name", "to_city__name")
        )
        popular_directions_by_transport = defaultdict(list)
        for row in popular_direction_rows:
            section = popular_directions_by_transport[row["transport_type"]]
            if len(section) >= 5:
                continue
            section.append(
                {
                    "from_city": row["from_city__name"],
                    "to_city": row["to_city__name"],
                    "tickets_count": row["total"],
                }
            )

        transport_sections = [
            {
                "transport_type": transport_type,
                "label": label,
                "tickets_count": transport_counts.get(transport_type, 0),
                "carriers": carriers_by_transport.get(transport_type, []),
                "popular_directions": popular_directions_by_transport.get(transport_type, []),
            }
            for transport_type, label in TRANSPORT_LABELS.items()
        ]

        stats_snapshot = {
            "cities_count": City.objects.count(),
            "carriers_count": Carrier.objects.filter(is_active=True).count(),
            "tickets_count": Ticket.objects.count(),
            "active_tickets_count": active_tickets.count(),
            "searches_count": RouteSearchLog.objects.count(),
            "tickets_by_transport": transport_counts,
            "transport_sections": transport_sections,
        }
        (cache_dir / "stats_snapshot.json").write_text(
            json.dumps(stats_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for city in City.objects.all().order_by("id"):
            city_tickets = active_tickets.filter(Q(from_city=city) | Q(to_city=city))
            related_destinations = city_tickets.annotate(
                related_city_id=Case(
                    When(from_city=city, then=F("to_city_id")),
                    default=F("from_city_id"),
                    output_field=IntegerField(),
                ),
                related_city_name=Case(
                    When(from_city=city, then=F("to_city__name")),
                    default=F("from_city__name"),
                    output_field=CharField(),
                ),
                related_city_slug=Case(
                    When(from_city=city, then=F("to_city__slug")),
                    default=F("from_city__slug"),
                    output_field=CharField(),
                ),
            )
            popular_destinations_rows = (
                related_destinations.values(
                    "related_city_id",
                    "related_city_name",
                    "related_city_slug",
                )
                .annotate(total=Count("id"))
                .order_by("-total", "related_city_name")[:6]
            )
            transport_mix_rows = (
                city_tickets.values("transport_type")
                .annotate(total=Count("id"))
                .order_by("transport_type")
            )
            payload = {
                "id": city.id,
                "name": city.name,
                "slug": city.slug,
                "region": city.region,
                "population": city.population,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "has_airport": city.has_airport,
                "has_international_airport": city.has_international_airport,
                "has_train_station": city.has_train_station,
                "has_bus_station": city.has_bus_station,
                "has_commuter_station": city.has_commuter_station,
                "is_rail_hub": city.is_rail_hub,
                "is_bus_hub": city.is_bus_hub,
                "available_transports": city.available_transports,
                "active_tickets_count": city_tickets.count(),
                "available_directions_count": related_destinations.values("related_city_id").distinct().count(),
                "tickets_by_transport": [
                    {"transport_type": row["transport_type"], "tickets_count": row["total"]}
                    for row in transport_mix_rows
                ],
                "city_energy": city_tickets.values("carrier_id").distinct().count(),
                "popular_destinations": [
                    {
                        "name": row["related_city_name"],
                        "slug": row["related_city_slug"],
                        "tickets_count": row["total"],
                    }
                    for row in popular_destinations_rows
                ],
            }
            (city_dir / f"{city.slug}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self.stdout.write(self.style.SUCCESS("Catalog snapshots refreshed."))
