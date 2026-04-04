from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.common.io import parse_iso_datetime, resolve_data_path
from apps.tickets.dto import UnifiedTicketDTO
from apps.tickets.models import Ticket
from apps.tickets.services.generation_service import DEFAULT_SEATS, FALLBACK_CARRIER_NAMES
from apps.tickets.services.signatures import (
    build_external_ticket_id,
    build_route_signature,
)

BULK_BATCH_SIZE = 5000
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


@dataclass(frozen=True)
class TicketImportStats:
    created: int
    skipped: int
    source_kind: str
    generation_batch: str | None


class CityResolver:
    def __init__(self, cities):
        buckets: dict[str, list[City]] = {}
        for city in cities:
            buckets.setdefault(city.name.casefold(), []).append(city)
            buckets.setdefault(city.slug.casefold(), []).append(city)
        self._cities = buckets
        for values in self._cities.values():
            values.sort(key=lambda city: (-city.population, city.region, city.id))

    def resolve(self, value: str | None) -> City | None:
        if not value:
            return None
        matches = self._cities.get(str(value).casefold())
        if not matches:
            return None
        return matches[0]

    def resolve_slug(self, value: str | None) -> str | None:
        city = self.resolve(value)
        return city.slug if city else None


class UnifiedTicketNormalizer:
    def __init__(self, *, city_resolver: CityResolver, default_batch: str):
        self.city_resolver = city_resolver
        self.default_batch = default_batch

    def normalize(
        self,
        item: dict,
        *,
        carrier_code: str,
        transport_type: str,
        source_name: str,
        line_number: int,
        generation_batch: str | None = None,
    ) -> UnifiedTicketDTO | None:
        if "departure_datetime" in item and "arrival_datetime" in item:
            return self._normalize_unified(
                item,
                carrier_code=carrier_code,
                transport_type=transport_type,
                generation_batch=generation_batch,
            )
        return self._normalize_legacy(
            item,
            carrier_code=carrier_code,
            transport_type=transport_type,
            source_name=source_name,
            line_number=line_number,
            generation_batch=generation_batch,
        )

    def _normalize_unified(
        self,
        item: dict,
        *,
        carrier_code: str,
        transport_type: str,
        generation_batch: str | None,
    ) -> UnifiedTicketDTO | None:
        payload = dict(item)
        payload["from_city"] = self.city_resolver.resolve_slug(payload.get("from_city"))
        payload["to_city"] = self.city_resolver.resolve_slug(payload.get("to_city"))
        if not payload["from_city"] or not payload["to_city"] or payload["from_city"] == payload["to_city"]:
            return None
        payload["carrier"] = payload.get("carrier") or carrier_code
        payload["transport_type"] = payload.get("transport_type") or transport_type
        payload["generation_batch"] = payload.get("generation_batch") or generation_batch or self.default_batch
        payload["route_signature"] = payload.get("route_signature") or build_route_signature(
            from_city=payload["from_city"],
            to_city=payload["to_city"],
            carrier=payload["carrier"],
            transport_type=payload["transport_type"],
            is_direct=bool(payload.get("is_direct", True)),
        )
        if not payload.get("external_id"):
            payload["external_id"] = build_external_ticket_id(
                {
                    "from_city": payload["from_city"],
                    "to_city": payload["to_city"],
                    "carrier": payload["carrier"],
                    "transport_type": payload["transport_type"],
                    "departure_datetime": payload["departure_datetime"],
                    "arrival_datetime": payload["arrival_datetime"],
                    "duration_minutes": int(payload["duration_minutes"]),
                    "price": int(payload["price"]),
                    "distance_km": int(payload["distance_km"]),
                    "is_direct": bool(payload.get("is_direct", True)),
                    "available_seats": int(payload.get("available_seats", DEFAULT_SEATS.get(payload["transport_type"], 32))),
                    "route_signature": payload["route_signature"],
                }
            )
        return UnifiedTicketDTO.from_dict(payload)

    def _normalize_legacy(
        self,
        item: dict,
        *,
        carrier_code: str,
        transport_type: str,
        source_name: str,
        line_number: int,
        generation_batch: str | None,
    ) -> UnifiedTicketDTO | None:
        from_city_slug = self.city_resolver.resolve_slug(item.get("from_city"))
        to_city_slug = self.city_resolver.resolve_slug(item.get("to_city"))
        if not from_city_slug or not to_city_slug or from_city_slug == to_city_slug:
            return None

        duration_minutes = int(item.get("duration_min") or item.get("duration_minutes") or 0)
        if duration_minutes <= 0:
            return None

        departure_at = self._parse_legacy_departure(item)
        arrival_at = parse_iso_datetime(item["arrival_datetime"]) if item.get("arrival_datetime") else departure_at + timedelta(minutes=duration_minutes)
        batch_id = generation_batch or item.get("generation_batch") or self.default_batch
        route_signature = item.get("route_signature") or build_route_signature(
            from_city=from_city_slug,
            to_city=to_city_slug,
            carrier=carrier_code,
            transport_type=transport_type,
            is_direct=bool(item.get("is_direct", True)),
        )
        dto_payload = {
            "from_city": from_city_slug,
            "to_city": to_city_slug,
            "carrier": carrier_code,
            "transport_type": transport_type,
            "departure_datetime": departure_at.isoformat(),
            "arrival_datetime": arrival_at.isoformat(),
            "duration_minutes": duration_minutes,
            "price": max(1, int(float(item.get("price_rub", item.get("price", 0))))),
            "distance_km": max(1, int(round(float(item.get("distance_km", 0))))),
            "is_direct": bool(item.get("is_direct", True)),
            "available_seats": max(0, int(item.get("available_seats", DEFAULT_SEATS.get(transport_type, 32)))),
            "is_active": bool(item.get("is_active", True)),
            "generation_batch": batch_id,
            "route_signature": route_signature,
            "generation_meta": {
                **dict(item.get("generation_meta") or {}),
                "legacy_import": True,
                "source_name": source_name,
                "source_line": line_number,
            },
        }
        external_id = item.get("external_id") or build_external_ticket_id(
            {
                "from_city": from_city_slug,
                "to_city": to_city_slug,
                "carrier": carrier_code,
                "transport_type": transport_type,
                "departure_datetime": dto_payload["departure_datetime"],
                "arrival_datetime": dto_payload["arrival_datetime"],
                "duration_minutes": duration_minutes,
                "price": dto_payload["price"],
                "distance_km": dto_payload["distance_km"],
                "is_direct": dto_payload["is_direct"],
                "available_seats": dto_payload["available_seats"],
                "route_signature": route_signature,
            }
        )
        return UnifiedTicketDTO(external_id=external_id, **dto_payload)

    def _parse_legacy_departure(self, item: dict):
        if item.get("departure_datetime"):
            return parse_iso_datetime(item["departure_datetime"])
        departure_date = item.get("departure_date")
        departure_time = item.get("departure_time", "00:00")
        if not departure_date:
            raise ValueError("Legacy ticket is missing departure_date.")
        dt = datetime.strptime(f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M")
        return timezone.make_aware(dt, timezone.get_current_timezone())


class TicketImportService:
    def __init__(self, *, jsonl_dir: str = "data/_tmp_ticket_jsonl"):
        self.jsonl_dir = resolve_data_path(jsonl_dir)

    def import_tickets(
        self,
        *,
        truncate: bool = False,
        batch_id: str | None = None,
        replace_batch: bool = False,
        max_tickets_per_file: int | None = None,
    ) -> TicketImportStats:
        if truncate:
            Ticket.objects.all().delete()

        city_resolver = CityResolver(City.objects.all())
        carriers = {
            carrier.code: carrier for carrier in Carrier.objects.filter(is_active=True)
        }
        if not carriers:
            raise CommandError("No carriers found. Import carriers before tickets.")

        generated_batch_dir = self._find_generated_batch_dir(batch_id)
        synced_at = timezone.now()
        current_now = timezone.now()
        created = 0
        skipped = 0
        batch: list[Ticket] = []

        if generated_batch_dir is not None:
            manifest = self._read_manifest(generated_batch_dir)
            active_batch = batch_id or manifest.get("batch_id") or generated_batch_dir.name
            if replace_batch:
                Ticket.objects.filter(generation_batch=active_batch).delete()
            normalizer = UnifiedTicketNormalizer(
                city_resolver=city_resolver,
                default_batch=active_batch,
            )
            iterator = self._iter_generated_sources(generated_batch_dir)
            source_kind = "generated_batch"
        else:
            active_batch = batch_id or "legacy-dataset"
            if replace_batch:
                Ticket.objects.filter(generation_batch=active_batch).delete()
            normalizer = UnifiedTicketNormalizer(
                city_resolver=city_resolver,
                default_batch=active_batch,
            )
            iterator = self._iter_legacy_sources(max_tickets_per_file=max_tickets_per_file)
            source_kind = "legacy_dataset"

        for source in iterator:
            carrier = carriers.get(source["carrier_code"])
            if carrier is None:
                raise CommandError(
                    f"Carrier {source['carrier_code']} not found for {source['source_name']}."
                )

            with transaction.atomic():
                for line_number, item in enumerate(source["records"], start=1):
                    if max_tickets_per_file is not None and line_number > max_tickets_per_file:
                        break
                    try:
                        dto = normalizer.normalize(
                            item,
                            carrier_code=source["carrier_code"],
                            transport_type=source["transport_type"],
                            source_name=source["source_name"],
                            line_number=line_number,
                            generation_batch=source.get("generation_batch"),
                        )
                    except (KeyError, TypeError, ValueError):
                        skipped += 1
                        continue

                    if dto is None:
                        skipped += 1
                        continue

                    from_city = city_resolver.resolve(dto.from_city)
                    to_city = city_resolver.resolve(dto.to_city)
                    if from_city is None or to_city is None:
                        skipped += 1
                        continue

                    departure_at = parse_iso_datetime(dto.departure_datetime)
                    arrival_at = parse_iso_datetime(dto.arrival_datetime)

                    batch.append(
                        Ticket(
                            external_id=dto.external_id,
                            carrier=carrier,
                            from_city=from_city,
                            to_city=to_city,
                            transport_type=dto.transport_type,
                            departure_datetime=departure_at,
                            arrival_datetime=arrival_at,
                            duration_minutes=dto.duration_minutes,
                            price=dto.price,
                            distance_km=dto.distance_km,
                            is_direct=dto.is_direct,
                            available_seats=dto.available_seats,
                            is_active=bool(dto.is_active) and departure_at >= current_now,
                            generation_batch=dto.generation_batch or active_batch,
                            route_signature=dto.route_signature,
                            generation_meta=dto.generation_meta,
                            last_synced_at=synced_at,
                        )
                    )

                    if len(batch) >= BULK_BATCH_SIZE:
                        created_delta, skipped_delta = self._flush_batch(batch)
                        created += created_delta
                        skipped += skipped_delta
                        batch.clear()

        if batch:
            created_delta, skipped_delta = self._flush_batch(batch)
            created += created_delta
            skipped += skipped_delta
            batch.clear()

        return TicketImportStats(
            created=created,
            skipped=skipped,
            source_kind=source_kind,
            generation_batch=active_batch,
        )

    def _flush_batch(self, batch: list[Ticket]) -> tuple[int, int]:
        external_ids = [ticket.external_id for ticket in batch]
        existing_ids = set(
            Ticket.objects.filter(external_id__in=external_ids).values_list("external_id", flat=True)
        )
        new_tickets = [ticket for ticket in batch if ticket.external_id not in existing_ids]
        if new_tickets:
            Ticket.objects.bulk_create(new_tickets, batch_size=BULK_BATCH_SIZE)
        return len(new_tickets), len(batch) - len(new_tickets)

    def _find_generated_batch_dir(self, batch_id: str | None) -> Path | None:
        generated_root = self.jsonl_dir / "generated"
        if not generated_root.exists():
            return None
        if batch_id:
            candidate = generated_root / batch_id
            return candidate if candidate.exists() else None

        candidates = [
            path
            for path in generated_root.iterdir()
            if path.is_dir() and (path / "manifest.json").exists()
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda path: ((path / "manifest.json").stat().st_mtime, path.name), reverse=True)
        return candidates[0]

    def _read_manifest(self, batch_dir: Path) -> dict:
        manifest_path = batch_dir / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _iter_generated_sources(self, batch_dir: Path):
        manifest = self._read_manifest(batch_dir)
        manifest_files = manifest.get("files") or []
        seen = set()
        for item in manifest_files:
            filename = item.get("path")
            if not filename:
                continue
            file_path = batch_dir / filename
            if not file_path.exists():
                continue
            seen.add(file_path.name)
            transport_type = item.get("transport_type") or file_path.stem.split("__", 1)[0]
            carrier_code = item.get("carrier") or file_path.stem.split("__", 1)[-1]
            yield {
                "transport_type": transport_type,
                "carrier_code": carrier_code,
                "source_name": file_path.name,
                "generation_batch": manifest.get("batch_id") or batch_dir.name,
                "records": self._iter_jsonl_records(file_path),
            }

        for file_path in sorted(batch_dir.glob("*.jsonl")):
            if file_path.name in seen:
                continue
            stem_parts = file_path.stem.split("__", 1)
            transport_type = stem_parts[0]
            carrier_code = stem_parts[-1]
            yield {
                "transport_type": transport_type,
                "carrier_code": carrier_code,
                "source_name": file_path.name,
                "generation_batch": manifest.get("batch_id") or batch_dir.name,
                "records": self._iter_jsonl_records(file_path),
            }

    def _iter_legacy_sources(self, *, max_tickets_per_file: int | None = None):
        del max_tickets_per_file
        for transport_type, relative_directory in SOURCE_DIRECTORIES.items():
            directory = resolve_data_path(relative_directory)
            if not directory.exists():
                continue

            for file_path in sorted(directory.glob("*.json")):
                jsonl_path = self.jsonl_dir / f"{JSONL_PREFIX[transport_type]}_{file_path.stem}.jsonl"
                payload = self._load_legacy_file(file_path, jsonl_path=jsonl_path)
                carrier_code = payload.get("id") or file_path.stem
                if jsonl_path.exists():
                    records = self._iter_jsonl_records(jsonl_path)
                else:
                    records = iter(payload.get("tickets", []))
                yield {
                    "transport_type": transport_type,
                    "carrier_code": carrier_code,
                    "source_name": file_path.name,
                    "generation_batch": payload.get("generation_batch"),
                    "records": records,
                }

    def _iter_jsonl_records(self, path: Path):
        with path.open(encoding="utf-8") as source:
            for line in source:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _load_legacy_file(self, file_path: Path, *, jsonl_path: Path | None = None):
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            if jsonl_path and jsonl_path.exists():
                return self._fallback_payload(file_path)
            raise CommandError(f"Failed to read {file_path}: {exc}") from exc

    def _fallback_payload(self, file_path: Path) -> dict:
        code = file_path.stem
        return {
            "id": code,
            "company": FALLBACK_CARRIER_NAMES.get(
                code,
                code.replace("_", " ").replace("-", " ").title(),
            ),
            "tickets": [],
            "source_recovery": "filename_fallback",
        }
