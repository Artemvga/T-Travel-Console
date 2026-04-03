import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.common.io import resolve_data_path
from apps.tickets.models import Ticket

BULK_BATCH_SIZE = 2500
SOURCE_DIRECTORIES = {
    "plane": "data/planes",
    "train": "data/trains",
    "bus": "data/buses/by_operator",
    "electric_train": "data/commuter_trains",
}
JSONL_PREFIX = {
    "plane": "plane",
    "train": "train",
    "bus": "bus",
    "electric_train": "electric_train",
}
DEFAULT_SEATS = {
    "plane": 72,
    "train": 180,
    "bus": 38,
    "electric_train": 120,
}


class Command(BaseCommand):
    help = "Import tickets from current data/*.json or data/_tmp_ticket_jsonl/*.jsonl."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jsonl-dir",
            default="data/_tmp_ticket_jsonl",
            help="Optional directory with generator JSONL files.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete all existing tickets before import.",
        )
        parser.add_argument(
            "--max-tickets-per-file",
            type=int,
            default=None,
            help="Optional cap per source file for faster local seeding.",
        )

    def handle(self, *args, **options):
        if not City.objects.exists():
            call_command("import_cities")
        if not Carrier.objects.exists():
            call_command("import_carriers")

        if options["truncate"]:
            Ticket.objects.all().delete()

        city_resolver = CityResolver(City.objects.all())
        carriers = {
            carrier.code: carrier for carrier in Carrier.objects.filter(is_active=True)
        }
        jsonl_dir = resolve_data_path(options["jsonl_dir"])
        max_tickets_per_file = options.get("max_tickets_per_file")
        imported = 0
        skipped = 0
        batch: list[Ticket] = []
        synced_at = timezone.now()

        for transport_type, relative_directory in SOURCE_DIRECTORIES.items():
            directory = resolve_data_path(relative_directory)
            if not directory.exists():
                continue

            for file_path in sorted(directory.glob("*.json")):
                payload = self._load_file(file_path)
                carrier_code = payload.get("id") or file_path.stem
                carrier = carriers.get(carrier_code)
                if carrier is None:
                    raise CommandError(f"Carrier {carrier_code} not found for {file_path}.")

                processed_for_file = 0
                ticket_iterable = self._iter_ticket_records(
                    payload=payload,
                    file_path=file_path,
                    transport_type=transport_type,
                    jsonl_dir=jsonl_dir,
                )

                with transaction.atomic():
                    for line_number, item in enumerate(ticket_iterable, start=1):
                        if max_tickets_per_file is not None and processed_for_file >= max_tickets_per_file:
                            break

                        from_city = city_resolver.resolve(item.get("from_city"))
                        to_city = city_resolver.resolve(item.get("to_city"))
                        if from_city is None or to_city is None or from_city.id == to_city.id:
                            skipped += 1
                            continue

                        duration_minutes = int(item.get("duration_min") or item.get("duration_minutes") or 0)
                        if duration_minutes <= 0:
                            skipped += 1
                            continue

                        departure_at = self._parse_departure(
                            item["departure_date"],
                            item["departure_time"],
                        )
                        arrival_at = departure_at + timedelta(minutes=duration_minutes)

                        batch.append(
                            Ticket(
                                external_id=self._build_external_id(
                                    carrier_code,
                                    item,
                                    line_number=line_number,
                                    source_name=file_path.name,
                                ),
                                carrier=carrier,
                                from_city=from_city,
                                to_city=to_city,
                                transport_type=transport_type,
                                departure_datetime=departure_at,
                                arrival_datetime=arrival_at,
                                duration_minutes=duration_minutes,
                                price=max(1, int(float(item.get("price_rub", item.get("price", 0))))),
                                distance_km=max(1, int(round(float(item.get("distance_km", 0))))),
                                is_direct=True,
                                available_seats=DEFAULT_SEATS.get(transport_type, 32),
                                is_active=departure_at >= timezone.now(),
                                last_synced_at=synced_at,
                            )
                        )
                        imported += 1
                        processed_for_file += 1

                        if len(batch) >= BULK_BATCH_SIZE:
                            Ticket.objects.bulk_create(batch, batch_size=BULK_BATCH_SIZE)
                            batch.clear()

                    if batch:
                        Ticket.objects.bulk_create(batch, batch_size=BULK_BATCH_SIZE)
                        batch.clear()

        self.stdout.write(
            self.style.SUCCESS(
                f"Tickets import completed: {imported} created, {skipped} skipped."
            )
        )

    def _iter_ticket_records(self, *, payload, file_path: Path, transport_type: str, jsonl_dir: Path):
        jsonl_path = jsonl_dir / f"{JSONL_PREFIX[transport_type]}_{file_path.stem}.jsonl"
        if jsonl_path.exists():
            with jsonl_path.open(encoding="utf-8") as source:
                for line in source:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
            return

        for item in payload.get("tickets", []):
            yield item

    def _load_file(self, file_path: Path):
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CommandError(f"Failed to read {file_path}: {exc}") from exc

    def _parse_departure(self, departure_date: str, departure_time: str):
        dt = datetime.strptime(
            f"{departure_date} {departure_time}",
            "%Y-%m-%d %H:%M",
        )
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def _build_external_id(self, carrier_code: str, item: dict, *, line_number: int, source_name: str) -> str:
        raw = "|".join(
            [
                carrier_code,
                source_name,
                str(line_number),
                str(item.get("from_city", "")),
                str(item.get("to_city", "")),
                str(item.get("departure_date", "")),
                str(item.get("departure_time", "")),
                str(item.get("price_rub", item.get("price", ""))),
            ]
        )
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return f"{carrier_code}-{digest}"


class CityResolver:
    def __init__(self, cities):
        buckets = {}
        for city in cities:
            buckets.setdefault(city.name.casefold(), []).append(city)
            buckets.setdefault(city.slug.casefold(), [city])
        self._cities = buckets
        for values in self._cities.values():
            values.sort(key=lambda city: (-city.population, city.region, city.id))

    def resolve(self, value: str | None) -> City | None:
        if not value:
            return None
        matches = self._cities.get(value.casefold())
        if not matches:
            return None
        return matches[0]
