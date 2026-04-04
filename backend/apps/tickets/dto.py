from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True, frozen=True)
class UnifiedTicketDTO:
    external_id: str
    from_city: str
    to_city: str
    carrier: str
    transport_type: str
    departure_datetime: str
    arrival_datetime: str
    duration_minutes: int
    price: int
    distance_km: int
    is_direct: bool
    available_seats: int
    is_active: bool
    generation_batch: str
    route_signature: str
    generation_meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "from_city": self.from_city,
            "to_city": self.to_city,
            "carrier": self.carrier,
            "transport_type": self.transport_type,
            "departure_datetime": self.departure_datetime,
            "arrival_datetime": self.arrival_datetime,
            "duration_minutes": self.duration_minutes,
            "price": self.price,
            "distance_km": self.distance_km,
            "is_direct": self.is_direct,
            "available_seats": self.available_seats,
            "is_active": self.is_active,
            "generation_batch": self.generation_batch,
            "route_signature": self.route_signature,
            "generation_meta": self.generation_meta,
        }

    def to_legacy_record(self, *, carrier_name: str) -> dict[str, Any]:
        departure_at = datetime.fromisoformat(self.departure_datetime)
        return {
            "from_city": self.from_city,
            "to_city": self.to_city,
            "company": carrier_name,
            "departure_date": departure_at.date().isoformat(),
            "departure_time": departure_at.time().isoformat(timespec="minutes"),
            "price_rub": self.price,
            "distance_km": self.distance_km,
            "duration_min": self.duration_minutes,
            "mode": self.transport_type,
            "external_id": self.external_id,
            "route_signature": self.route_signature,
            "generation_batch": self.generation_batch,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UnifiedTicketDTO":
        return cls(
            external_id=str(payload["external_id"]),
            from_city=str(payload["from_city"]),
            to_city=str(payload["to_city"]),
            carrier=str(payload["carrier"]),
            transport_type=str(payload["transport_type"]),
            departure_datetime=str(payload["departure_datetime"]),
            arrival_datetime=str(payload["arrival_datetime"]),
            duration_minutes=int(payload["duration_minutes"]),
            price=max(1, int(payload["price"])),
            distance_km=max(1, int(payload["distance_km"])),
            is_direct=bool(payload.get("is_direct", True)),
            available_seats=max(0, int(payload.get("available_seats", 0))),
            is_active=bool(payload.get("is_active", True)),
            generation_batch=str(payload.get("generation_batch", "")).strip(),
            route_signature=str(payload["route_signature"]),
            generation_meta=dict(payload.get("generation_meta") or {}),
        )
