from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.common.io import load_json
from apps.cities.models import City


class Command(BaseCommand):
    help = "Import cities from the root data/cities/cities.json dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="data/cities/cities.json",
            help="Relative path from backend/ or absolute path to cities JSON.",
        )

    def handle(self, *args, **options):
        payload = load_json(options["path"])
        cities = payload["cities"] if isinstance(payload, dict) else payload
        created = 0
        updated = 0
        seen_slugs: set[str] = set()

        with transaction.atomic():
            for index, item in enumerate(cities, start=1):
                slug = self._build_unique_slug(
                    item["name"],
                    item.get("region", ""),
                    index=index,
                    seen_slugs=seen_slugs,
                )
                city, is_created = City.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": item["name"],
                        "region": item.get("region", ""),
                        "population": int(item.get("population", 0) or 0),
                        "latitude": float(item.get("lat", item.get("latitude"))),
                        "longitude": float(item.get("lon", item.get("longitude"))),
                        "has_airport": bool(item.get("has_airport", False)),
                        "has_international_airport": bool(
                            item.get("has_international_airport", False)
                        ),
                        "has_train_station": bool(item.get("has_train_station", False)),
                        "has_bus_station": bool(item.get("has_bus_station", False)),
                        "has_commuter_station": bool(item.get("has_commuter_station", False)),
                        "is_rail_hub": bool(item.get("is_rail_hub", False)),
                        "is_bus_hub": bool(item.get("is_bus_hub", False)),
                    },
                )
                seen_slugs.add(city.slug)
                created += int(is_created)
                updated += int(not is_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cities import completed: {created} created, {updated} updated."
            )
        )

    def _build_unique_slug(
        self,
        name: str,
        region: str,
        *,
        index: int,
        seen_slugs: set[str],
    ) -> str:
        base = slugify(f"{name}-{region}") or slugify(name) or f"city-{index}"
        slug = base
        suffix = 2
        while slug in seen_slugs:
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug
