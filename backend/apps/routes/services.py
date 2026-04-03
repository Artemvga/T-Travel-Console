from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.cities.models import City
from apps.cities.search_utils import resolve_alias_name
from apps.tickets.models import Ticket


MIN_TRANSFER_BUFFER_MINUTES = {
    Ticket.TransportType.PLANE: 75,
    Ticket.TransportType.TRAIN: 35,
    Ticket.TransportType.BUS: 25,
    Ticket.TransportType.ELECTRIC_TRAIN: 20,
}
SEARCH_WINDOWS_HOURS = (12, 24, 72, 168)
MAX_QUERY_ROWS = 180
MAX_CANDIDATES_TOTAL = 24
PER_DESTINATION_LIMIT = 3
MAX_STATE_EXPANSIONS = 1800
MAX_RESULTS = 8


@dataclass(slots=True)
class RoutePath:
    segments: list[Ticket]
    total_price: int
    total_duration_minutes: int
    total_distance_km: int
    transfers_count: int
    score: float
    ready_at: datetime


@dataclass(slots=True)
class SearchState:
    current_city: City
    ready_at: datetime
    first_departure_at: datetime | None
    last_arrival_at: datetime | None
    segments: tuple[Ticket, ...]
    visited_city_ids: frozenset[int]
    total_price: int
    total_distance_km: int

    @property
    def total_duration_minutes(self) -> int:
        if self.first_departure_at is None or self.last_arrival_at is None:
            return 0
        return int(
            (self.last_arrival_at - self.first_departure_at).total_seconds() // 60
        )


def resolve_city(value: str) -> City:
    query = value.strip()
    if not query:
        raise ValueError("Город не указан.")

    try:
        return City.objects.get(slug__iexact=query)
    except City.DoesNotExist:
        pass

    exact_matches = list(City.objects.filter(name__iexact=query).order_by("-population", "region", "id"))
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(
            f"Найдено несколько городов с названием {value}. Выберите город из подсказок."
        )

    alias_name = resolve_alias_name(query)
    if alias_name:
        alias_matches = list(
            City.objects.filter(name__iexact=alias_name).order_by("-population", "region", "id")
        )
        if len(alias_matches) == 1:
            return alias_matches[0]

    raise ValueError(f"Город {value} не найден.")


def _ticket_segment(ticket: Ticket) -> dict:
    return {
        "external_id": ticket.external_id,
        "carrier": ticket.carrier.name,
        "carrier_code": ticket.carrier.code,
        "transport_type": ticket.transport_type,
        "from_city": ticket.from_city.name,
        "from_city_slug": ticket.from_city.slug,
        "from_city_region": ticket.from_city.region,
        "to_city": ticket.to_city.name,
        "to_city_slug": ticket.to_city.slug,
        "to_city_region": ticket.to_city.region,
        "from_coordinates": [
            round(ticket.from_city.latitude, 6),
            round(ticket.from_city.longitude, 6),
        ],
        "to_coordinates": [
            round(ticket.to_city.latitude, 6),
            round(ticket.to_city.longitude, 6),
        ],
        "departure_datetime": ticket.departure_datetime.isoformat(),
        "arrival_datetime": ticket.arrival_datetime.isoformat(),
        "price": ticket.price,
        "distance_km": ticket.distance_km,
        "duration_minutes": ticket.duration_minutes,
        "is_direct": ticket.is_direct,
        "available_seats": ticket.available_seats,
    }


def _serialize_path(path: RoutePath) -> dict:
    waypoints = [
        {
            "name": path.segments[0].from_city.name,
            "slug": path.segments[0].from_city.slug,
            "region": path.segments[0].from_city.region,
            "latitude": round(path.segments[0].from_city.latitude, 6),
            "longitude": round(path.segments[0].from_city.longitude, 6),
        }
    ]
    waypoints.extend(
        {
            "name": ticket.to_city.name,
            "slug": ticket.to_city.slug,
            "region": ticket.to_city.region,
            "latitude": round(ticket.to_city.latitude, 6),
            "longitude": round(ticket.to_city.longitude, 6),
        }
        for ticket in path.segments
    )

    return {
        "total_price": path.total_price,
        "total_duration_minutes": path.total_duration_minutes,
        "total_distance_km": path.total_distance_km,
        "transfers_count": path.transfers_count,
        "waypoints": waypoints,
        "path_coordinates": [
            [waypoint["latitude"], waypoint["longitude"]] for waypoint in waypoints
        ],
        "segments": [_ticket_segment(ticket) for ticket in path.segments],
    }


def _path_signature(segments: list[Ticket] | tuple[Ticket, ...]) -> tuple[str, ...]:
    return tuple(ticket.external_id for ticket in segments)


def _path_city_ids(segments: list[Ticket]) -> set[int]:
    city_ids = {segments[0].from_city_id}
    city_ids.update(ticket.to_city_id for ticket in segments)
    return city_ids


def _min_buffer_minutes(segment: Ticket) -> int:
    return MIN_TRANSFER_BUFFER_MINUTES.get(segment.transport_type, 30)


def _route_score(
    *,
    total_price: int,
    total_duration_minutes: int,
    transfers_count: int,
    priority: str,
) -> float:
    if priority == "cheapest":
        return total_price + transfers_count * 250 + total_duration_minutes * 0.08
    if priority == "fastest":
        return total_duration_minutes + transfers_count * 45 + total_price * 0.015
    return total_price * 0.42 + total_duration_minutes * 0.48 + transfers_count * 100


def _build_path(segments: list[Ticket], priority: str) -> RoutePath:
    total_price = sum(segment.price for segment in segments)
    total_distance_km = sum(segment.distance_km for segment in segments)
    transfers_count = max(0, len(segments) - 1)
    total_duration_minutes = int(
        (segments[-1].arrival_datetime - segments[0].departure_datetime).total_seconds() // 60
    )
    ready_at = segments[-1].arrival_datetime + timedelta(
        minutes=_min_buffer_minutes(segments[-1])
    )
    return RoutePath(
        segments=segments,
        total_price=total_price,
        total_duration_minutes=total_duration_minutes,
        total_distance_km=total_distance_km,
        transfers_count=transfers_count,
        score=_route_score(
            total_price=total_price,
            total_duration_minutes=total_duration_minutes,
            transfers_count=transfers_count,
            priority=priority,
        ),
        ready_at=ready_at,
    )


def _sort_paths(paths: list[RoutePath], priority: str) -> list[RoutePath]:
    if priority == "cheapest":
        return sorted(
            paths,
            key=lambda item: (
                item.total_price,
                item.total_duration_minutes,
                item.transfers_count,
            ),
        )
    if priority == "fastest":
        return sorted(
            paths,
            key=lambda item: (
                item.total_duration_minutes,
                item.total_price,
                item.transfers_count,
            ),
        )
    return sorted(
        paths,
        key=lambda item: (
            item.score,
            item.total_duration_minutes,
            item.total_price,
        ),
    )


def _state_score(state: SearchState, priority: str) -> float:
    return _route_score(
        total_price=state.total_price,
        total_duration_minutes=state.total_duration_minutes,
        transfers_count=max(0, len(state.segments) - 1),
        priority=priority,
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _heuristic_score(origin: City, target: City, priority: str) -> float:
    distance = _haversine_km(
        origin.latitude,
        origin.longitude,
        target.latitude,
        target.longitude,
    )
    if priority == "cheapest":
        return distance * 1.4
    if priority == "fastest":
        return distance / 520 * 60
    return distance * 0.35


def _candidate_sort_key(ticket: Ticket, target_city: City, priority: str):
    direct_rank = 0 if ticket.to_city_id == target_city.id else 1
    remaining_distance = _haversine_km(
        ticket.to_city.latitude,
        ticket.to_city.longitude,
        target_city.latitude,
        target_city.longitude,
    )

    if priority == "cheapest":
        return (
            direct_rank,
            ticket.price,
            remaining_distance,
            ticket.departure_datetime,
            ticket.duration_minutes,
        )

    if priority == "fastest":
        return (
            direct_rank,
            remaining_distance,
            ticket.duration_minutes,
            ticket.departure_datetime,
            ticket.price,
        )

    return (
        direct_rank,
        remaining_distance,
        ticket.departure_datetime,
        ticket.price,
        ticket.duration_minutes,
    )


def _fetch_candidate_tickets(
    *,
    current_city: City,
    target_city: City,
    ready_at: datetime,
    visited_city_ids: frozenset[int],
    priority: str,
    carrier_codes: list[str],
    transport_types: list[str],
) -> list[Ticket]:
    queryset = Ticket.objects.filter(
        is_active=True,
        available_seats__gt=0,
        from_city_id=current_city.id,
        departure_datetime__gte=ready_at,
    ).exclude(to_city_id__in=visited_city_ids)

    if carrier_codes:
        queryset = queryset.filter(
            Q(carrier__code__in=carrier_codes)
            | Q(transport_type=Ticket.TransportType.BUS)
        )

    if transport_types:
        queryset = queryset.filter(transport_type__in=transport_types)

    queryset = queryset.select_related("carrier", "from_city", "to_city")

    candidates: list[Ticket] = []
    seen_ids: set[int] = set()
    per_destination: dict[int, int] = defaultdict(int)

    for hours in SEARCH_WINDOWS_HOURS:
        batch = list(
            queryset.filter(departure_datetime__lt=ready_at + timedelta(hours=hours))
            .order_by("departure_datetime", "price")[:MAX_QUERY_ROWS]
        )
        if not batch:
            continue

        batch.sort(key=lambda ticket: _candidate_sort_key(ticket, target_city, priority))
        for ticket in batch:
            if ticket.id in seen_ids:
                continue

            destination_limit = 4 if ticket.to_city_id == target_city.id else PER_DESTINATION_LIMIT
            if per_destination[ticket.to_city_id] >= destination_limit:
                continue

            candidates.append(ticket)
            seen_ids.add(ticket.id)
            per_destination[ticket.to_city_id] += 1

            if len(candidates) >= MAX_CANDIDATES_TOTAL:
                return candidates

        if len(candidates) >= 6:
            break

    return candidates


def _search_paths(
    *,
    start_city: City,
    target_city: City,
    departure_after: datetime,
    priority: str,
    carrier_codes: list[str],
    transport_types: list[str],
    max_segments: int,
    max_results: int = MAX_RESULTS,
    initial_visited_ids: set[int] | None = None,
) -> list[RoutePath]:
    if max_segments < 1:
        return []

    initial_state = SearchState(
        current_city=start_city,
        ready_at=departure_after,
        first_departure_at=None,
        last_arrival_at=None,
        segments=(),
        visited_city_ids=frozenset(initial_visited_ids or {start_city.id}),
        total_price=0,
        total_distance_km=0,
    )
    queue: list[tuple[float, int, int, SearchState]] = [
        (0.0, 0, 0, initial_state)
    ]
    counter = itertools.count(start=1)
    expansions = 0
    completed: list[RoutePath] = []
    completed_signatures: set[tuple[str, ...]] = set()
    best_progress: dict[tuple[int, int], float] = {}
    best_complete_score: float | None = None

    while queue and expansions < MAX_STATE_EXPANSIONS:
        estimated_score, _, _, state = heapq.heappop(queue)
        expansions += 1

        if (
            best_complete_score is not None
            and len(completed) >= max_results
            and estimated_score > best_complete_score * 1.25
        ):
            break

        if state.current_city.id == target_city.id and state.segments:
            path = _build_path(list(state.segments), priority)
            signature = _path_signature(path.segments)
            if signature not in completed_signatures:
                completed.append(path)
                completed_signatures.add(signature)
                if best_complete_score is None:
                    best_complete_score = path.score
                else:
                    best_complete_score = min(best_complete_score, path.score)
            continue

        if len(state.segments) >= max_segments:
            continue

        progress_key = (state.current_city.id, len(state.segments))
        current_score = _state_score(state, priority)
        known_score = best_progress.get(progress_key)
        if known_score is not None and current_score > known_score * 1.18:
            continue
        best_progress[progress_key] = (
            current_score if known_score is None else min(known_score, current_score)
        )

        candidates = _fetch_candidate_tickets(
            current_city=state.current_city,
            target_city=target_city,
            ready_at=state.ready_at,
            visited_city_ids=state.visited_city_ids,
            priority=priority,
            carrier_codes=carrier_codes,
            transport_types=transport_types,
        )
        for ticket in candidates:
            first_departure_at = state.first_departure_at or ticket.departure_datetime
            next_state = SearchState(
                current_city=ticket.to_city,
                ready_at=ticket.arrival_datetime + timedelta(minutes=_min_buffer_minutes(ticket)),
                first_departure_at=first_departure_at,
                last_arrival_at=ticket.arrival_datetime,
                segments=state.segments + (ticket,),
                visited_city_ids=state.visited_city_ids | {ticket.to_city_id},
                total_price=state.total_price + ticket.price,
                total_distance_km=state.total_distance_km + ticket.distance_km,
            )
            path_score = _state_score(next_state, priority)
            estimated_total = path_score + _heuristic_score(
                ticket.to_city,
                target_city,
                priority,
            )
            heapq.heappush(
                queue,
                (
                    estimated_total,
                    len(next_state.segments),
                    next(counter),
                    next_state,
                ),
            )

    return _sort_paths(completed, priority)[:max_results]


def build_routes(payload: dict) -> dict:
    from_city = resolve_city(payload["from_city"])
    to_city = resolve_city(payload["to_city"])
    via_city = resolve_city(payload["via_city"]) if payload.get("via_city") else None
    departure_after = timezone.make_aware(
        datetime.combine(payload["departure_date"], payload["departure_time"])
    )

    direct_only = payload.get("direct_only", False)
    allow_transfers = payload.get("allow_transfers", True)
    max_transfers = min(payload.get("max_transfers", 2), 5)
    max_segments = 1 if direct_only or not allow_transfers else min(6, max_transfers + 1)
    carrier_codes = payload.get("preferred_carriers") or []
    transport_types = payload.get("preferred_transport_types") or []

    if via_city and max_segments < 2:
        return {
            "status": "empty",
            "query": {
                "from_city": from_city.name,
                "from_city_slug": from_city.slug,
                "to_city": to_city.name,
                "to_city_slug": to_city.slug,
                "via_city": via_city.name,
                "via_city_slug": via_city.slug,
                "departure_date": payload["departure_date"].isoformat(),
                "departure_time": payload["departure_time"].isoformat(timespec="minutes"),
                "priority": payload["priority"],
            },
            "message": "Для маршрута через транзитный город нужен минимум один переход.",
            "best_route": None,
            "alternative_routes": [],
        }

    if via_city is None:
        ranked_paths = _search_paths(
            start_city=from_city,
            target_city=to_city,
            departure_after=departure_after,
            priority=payload["priority"],
            carrier_codes=carrier_codes,
            transport_types=transport_types,
            max_segments=max_segments,
            max_results=MAX_RESULTS,
        )
    else:
        first_leg_paths = _search_paths(
            start_city=from_city,
            target_city=via_city,
            departure_after=departure_after,
            priority=payload["priority"],
            carrier_codes=carrier_codes,
            transport_types=transport_types,
            max_segments=max_segments - 1,
            max_results=MAX_RESULTS,
        )
        combined_paths: list[RoutePath] = []
        combined_signatures: set[tuple[str, ...]] = set()

        for first_leg in first_leg_paths:
            remaining_segments = max_segments - len(first_leg.segments)
            if remaining_segments < 1:
                continue

            second_leg_paths = _search_paths(
                start_city=via_city,
                target_city=to_city,
                departure_after=first_leg.ready_at,
                priority=payload["priority"],
                carrier_codes=carrier_codes,
                transport_types=transport_types,
                max_segments=remaining_segments,
                max_results=MAX_RESULTS,
                initial_visited_ids=_path_city_ids(first_leg.segments),
            )
            for second_leg in second_leg_paths:
                merged_path = _build_path(
                    first_leg.segments + second_leg.segments,
                    payload["priority"],
                )
                signature = _path_signature(merged_path.segments)
                if signature in combined_signatures:
                    continue
                combined_paths.append(merged_path)
                combined_signatures.add(signature)

        ranked_paths = _sort_paths(combined_paths, payload["priority"])

    if not ranked_paths:
        transit_suffix = f" через {via_city.name}" if via_city else ""
        return {
            "status": "empty",
            "query": {
                "from_city": from_city.name,
                "from_city_slug": from_city.slug,
                "to_city": to_city.name,
                "to_city_slug": to_city.slug,
                "via_city": via_city.name if via_city else None,
                "via_city_slug": via_city.slug if via_city else None,
                "departure_date": payload["departure_date"].isoformat(),
                "departure_time": payload["departure_time"].isoformat(timespec="minutes"),
                "priority": payload["priority"],
            },
            "message": f"Маршруты{transit_suffix} по выбранным условиям не найдены.",
            "best_route": None,
            "alternative_routes": [],
        }

    best_route = ranked_paths[0]
    alternatives = ranked_paths[1:MAX_RESULTS] if payload.get("show_alternatives", True) else []

    return {
        "status": "success",
        "query": {
            "from_city": from_city.name,
            "from_city_slug": from_city.slug,
            "to_city": to_city.name,
            "to_city_slug": to_city.slug,
            "via_city": via_city.name if via_city else None,
            "via_city_slug": via_city.slug if via_city else None,
            "departure_date": payload["departure_date"].isoformat(),
            "departure_time": payload["departure_time"].isoformat(timespec="minutes"),
            "priority": payload["priority"],
        },
        "message": (
            f"Найдено {len(ranked_paths)} маршрутов."
            if via_city is None
            else f"Найдено {len(ranked_paths)} маршрутов через {via_city.name}."
        ),
        "best_route": _serialize_path(best_route),
        "alternative_routes": [_serialize_path(route) for route in alternatives],
    }
