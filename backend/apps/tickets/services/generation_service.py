from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from django.utils.text import slugify

from apps.tickets.dto import UnifiedTicketDTO
from apps.tickets.services.signatures import (
    build_external_ticket_id,
    build_route_signature,
)

NATIONAL_AIR_HUBS = {
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
}

FORCED_ROUTE_PAIRS = {
    "plane": [
        ("Новосибирск", "Москва"),
        ("Новосибирск", "Екатеринбург"),
        ("Москва", "Санкт-Петербург"),
        ("Новосибирск", "Томск"),
        ("Новосибирск", "Владивосток"),
        ("Москва", "Калининград"),
    ],
    "train": [
        ("Новосибирск", "Москва"),
        ("Новосибирск", "Екатеринбург"),
        ("Москва", "Санкт-Петербург"),
        ("Новосибирск", "Томск"),
        ("Екатеринбург", "Москва"),
        ("Иркутск", "Улан-Удэ"),
    ],
    "bus": [
        ("Новосибирск", "Томск"),
        ("Новосибирск", "Барнаул"),
        ("Новосибирск", "Кемерово"),
        ("Томск", "Кемерово"),
        ("Москва", "Тула"),
        ("Москва", "Ярославль"),
        ("Санкт-Петербург", "Великий Новгород"),
    ],
    "electric_train": [
        ("Новосибирск", "Томск"),
        ("Москва", "Тула"),
        ("Москва", "Ярославль"),
        ("Санкт-Петербург", "Великий Новгород"),
    ],
}

DEFAULT_SEATS = {
    "plane": 72,
    "train": 180,
    "bus": 38,
    "electric_train": 120,
}

FALLBACK_CARRIER_NAMES = {
    "aeroflot": "Аэрофлот",
    "s7": "S7 Airlines",
    "pobeda": "Победа",
    "rzd": "РЖД",
    "rzd_prigorod": "РЖД Пригород",
    "central_ppk": "ЦППК",
}

HOUR_WINDOWS = {
    "plane": [6, 7, 9, 11, 13, 15, 17, 19, 21],
    "train": [5, 8, 11, 14, 17, 20, 22],
    "electric_train": [6, 7, 9, 13, 17, 19],
    "bus": [6, 8, 10, 12, 14, 16, 18, 20],
}

MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]


@dataclass(frozen=True)
class City:
    name: str
    slug: str
    region: str
    lat: float
    lon: float
    population: int
    has_airport: bool
    has_international_airport: bool
    has_train_station: bool
    has_bus_station: bool
    has_commuter_station: bool
    is_rail_hub: bool
    is_bus_hub: bool

    @property
    def key(self) -> tuple[str, str]:
        return (self.name.casefold(), self.region.casefold())


@dataclass(frozen=True)
class CarrierDocument:
    code: str
    name: str
    transport_type: str
    metadata: dict
    legacy_output_path: Path


@dataclass(frozen=True)
class GenerationConfig:
    total: int
    start_date: datetime
    end_date: datetime
    seed: int
    batch_id: str
    tmp_dir: Path
    materialize_json: bool = False
    transport_types: tuple[str, ...] = ()
    weights: dict[str, int] | None = None


@dataclass(frozen=True)
class GenerationResult:
    batch_id: str
    batch_dir: Path
    manifest_path: Path
    total_generated: int
    counts_by_transport: dict[str, int]
    counts_by_carrier: dict[str, int]


def build_city_slug(name: str, region: str, *, index: int, seen_slugs: set[str]) -> str:
    base = slugify(f"{name}-{region}") or slugify(name) or f"city-{index}"
    slug = base
    suffix = 2
    while slug in seen_slugs:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def load_cities(data_dir: Path) -> list[City]:
    payload = json.loads((data_dir / "cities" / "cities.json").read_text(encoding="utf-8"))
    cities_payload = payload.get("cities", payload)
    seen_slugs: set[str] = set()
    cities: list[City] = []
    for index, item in enumerate(cities_payload, start=1):
        slug = build_city_slug(
            item["name"],
            item.get("region", ""),
            index=index,
            seen_slugs=seen_slugs,
        )
        seen_slugs.add(slug)
        cities.append(
            City(
                name=item["name"],
                slug=slug,
                region=item.get("region", ""),
                lat=float(item.get("lat", item.get("latitude", 0))),
                lon=float(item.get("lon", item.get("longitude", 0))),
                population=int(item.get("population", 0) or 0),
                has_airport=bool(item.get("has_airport", False)),
                has_international_airport=bool(item.get("has_international_airport", False)),
                has_train_station=bool(item.get("has_train_station", False)),
                has_bus_station=bool(item.get("has_bus_station", False)),
                has_commuter_station=bool(item.get("has_commuter_station", False)),
                is_rail_hub=bool(item.get("is_rail_hub", False)),
                is_bus_hub=bool(item.get("is_bus_hub", False)),
            )
        )
    return cities


def load_bus_operators(data_dir: Path) -> list[CarrierDocument]:
    index_path = data_dir / "buses" / "operators_index.json"
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        operators = payload.get("operators", [])
        return [
            CarrierDocument(
                code=item["id"],
                name=item.get("company") or item["id"],
                transport_type="bus",
                metadata={key: value for key, value in item.items() if key != "tickets"},
                legacy_output_path=data_dir / "buses" / "by_operator" / f"{item['id']}.json",
            )
            for item in operators
        ]

    docs = load_docs(data_dir / "buses" / "by_operator", transport_type="bus")
    return list(docs.values())


def load_docs(directory: Path, *, transport_type: str) -> dict[str, CarrierDocument]:
    docs: dict[str, CarrierDocument] = {}
    if not directory.exists():
        return docs

    for file_path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        code = payload.get("id") or file_path.stem
        name = (
            payload.get("company")
            or payload.get("name")
            or FALLBACK_CARRIER_NAMES.get(code)
            or code.replace("_", " ").replace("-", " ").title()
        )
        docs[code] = CarrierDocument(
            code=code,
            name=name,
            transport_type=transport_type,
            metadata={key: value for key, value in payload.items() if key != "tickets"},
            legacy_output_path=file_path,
        )
    return docs


def haversine_km(a: City, b: City) -> float:
    radius = 6371.0
    phi1 = math.radians(a.lat)
    phi2 = math.radians(b.lat)
    delta_phi = math.radians(b.lat - a.lat)
    delta_lambda = math.radians(b.lon - a.lon)
    aa = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


def sorted_neighbors(cities: list[City]) -> dict[tuple[str, str], list[tuple[float, City]]]:
    neighbors: dict[tuple[str, str], list[tuple[float, City]]] = {}
    for city in cities:
        distances = []
        for other in cities:
            if other.key == city.key:
                continue
            distances.append((haversine_km(city, other), other))
        distances.sort(key=lambda item: item[0])
        neighbors[city.key] = distances
    return neighbors


def merge_bidirectional(
    edges: set[tuple[tuple[str, str], tuple[str, str]]]
) -> set[tuple[tuple[str, str], tuple[str, str]]]:
    bidirectional = set(edges)
    bidirectional.update((destination, origin) for origin, destination in edges)
    return bidirectional


def add_forced_edges(
    edges: set[tuple[tuple[str, str], tuple[str, str]]],
    city_by_name: dict[str, City],
    transport_type: str,
) -> set[tuple[tuple[str, str], tuple[str, str]]]:
    result = set(edges)
    for origin_name, destination_name in FORCED_ROUTE_PAIRS.get(transport_type, []):
        origin = city_by_name.get(origin_name.casefold())
        destination = city_by_name.get(destination_name.casefold())
        if origin and destination and origin.key != destination.key:
            result.add((origin.key, destination.key))
            result.add((destination.key, origin.key))
    return result


def _pick_neighbors(
    origin: City,
    neighbors: dict[tuple[str, str], list[tuple[float, City]]],
    *,
    min_distance: float,
    max_distance: float,
    max_count: int,
    predicate=None,
) -> list[City]:
    picked: list[City] = []
    for distance, candidate in neighbors[origin.key]:
        if distance < min_distance or distance > max_distance:
            continue
        if predicate and not predicate(candidate, distance):
            continue
        picked.append(candidate)
        if len(picked) >= max_count:
            break
    return picked


def build_bus_edges(
    cities: list[City],
    neighbors: dict[tuple[str, str], list[tuple[float, City]]],
    city_by_name: dict[str, City],
) -> list[tuple[City, City]]:
    edges: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    bus_cities = [city for city in cities if city.has_bus_station]

    for city in bus_cities:
        max_count = 6 if city.is_bus_hub else 4
        max_distance = 420 if city.is_bus_hub else 260
        preferred = _pick_neighbors(
            city,
            neighbors,
            min_distance=20,
            max_distance=max_distance,
            max_count=max_count,
            predicate=lambda candidate, distance: candidate.has_bus_station
            and (candidate.region == city.region or distance <= 150),
        )
        if len(preferred) < max_count:
            preferred.extend(
                candidate
                for candidate in _pick_neighbors(
                    city,
                    neighbors,
                    min_distance=20,
                    max_distance=max_distance,
                    max_count=max_count,
                    predicate=lambda candidate, _: candidate.has_bus_station,
                )
                if candidate not in preferred
            )
        for candidate in preferred[:max_count]:
            edges.add((city.key, candidate.key))

    edges = add_forced_edges(merge_bidirectional(edges), city_by_name, "bus")
    indexed = {city.key: city for city in cities}
    return [(indexed[origin], indexed[destination]) for origin, destination in sorted(edges)]


def build_train_edges(
    cities: list[City],
    neighbors: dict[tuple[str, str], list[tuple[float, City]]],
    city_by_name: dict[str, City],
) -> list[tuple[City, City]]:
    edges: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    rail_cities = [city for city in cities if city.has_train_station]

    for city in rail_cities:
        max_count = 7 if city.is_rail_hub else 4
        max_distance = 2200 if city.is_rail_hub else 1400
        preferred = _pick_neighbors(
            city,
            neighbors,
            min_distance=70,
            max_distance=max_distance,
            max_count=max_count,
            predicate=lambda candidate, distance: candidate.has_train_station
            and (
                candidate.region == city.region
                or candidate.is_rail_hub
                or city.is_rail_hub
                or distance <= 900
            ),
        )
        if len(preferred) < max_count:
            preferred.extend(
                candidate
                for candidate in _pick_neighbors(
                    city,
                    neighbors,
                    min_distance=70,
                    max_distance=max_distance,
                    max_count=max_count,
                    predicate=lambda candidate, _: candidate.has_train_station,
                )
                if candidate not in preferred
            )
        for candidate in preferred[:max_count]:
            edges.add((city.key, candidate.key))

    edges = add_forced_edges(merge_bidirectional(edges), city_by_name, "train")
    indexed = {city.key: city for city in cities}
    return [(indexed[origin], indexed[destination]) for origin, destination in sorted(edges)]


def build_electric_edges(
    cities: list[City],
    neighbors: dict[tuple[str, str], list[tuple[float, City]]],
    city_by_name: dict[str, City],
) -> list[tuple[City, City]]:
    edges: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    commuter_cities = [city for city in cities if city.has_commuter_station]

    for city in commuter_cities:
        preferred = _pick_neighbors(
            city,
            neighbors,
            min_distance=10,
            max_distance=180,
            max_count=3,
            predicate=lambda candidate, _: candidate.has_commuter_station and candidate.region == city.region,
        )
        if len(preferred) < 2:
            preferred.extend(
                candidate
                for candidate in _pick_neighbors(
                    city,
                    neighbors,
                    min_distance=10,
                    max_distance=250,
                    max_count=3,
                    predicate=lambda candidate, _: candidate.has_commuter_station,
                )
                if candidate not in preferred
            )
        for candidate in preferred[:3]:
            edges.add((city.key, candidate.key))

    edges = add_forced_edges(merge_bidirectional(edges), city_by_name, "electric_train")
    indexed = {city.key: city for city in cities}
    return [(indexed[origin], indexed[destination]) for origin, destination in sorted(edges)]


def build_plane_edges(
    cities: list[City],
    neighbors: dict[tuple[str, str], list[tuple[float, City]]],
    city_by_name: dict[str, City],
) -> list[tuple[City, City]]:
    edges: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    airport_cities = [city for city in cities if city.has_airport]
    international_keys = {city.key for city in airport_cities if city.has_international_airport}
    national_keys = {
        city.key
        for city in airport_cities
        if city.name in NATIONAL_AIR_HUBS or city.has_international_airport
    }

    for city in airport_cities:
        for candidate in _pick_neighbors(
            city,
            neighbors,
            min_distance=250,
            max_distance=5200,
            max_count=6 if city.has_international_airport else 4,
            predicate=lambda candidate, _: candidate.has_airport and candidate.key in national_keys,
        ):
            edges.add((city.key, candidate.key))

        extra_neighbors = _pick_neighbors(
            city,
            neighbors,
            min_distance=250,
            max_distance=3800 if city.has_international_airport else 2600,
            max_count=6 if city.has_international_airport else 3,
            predicate=lambda candidate, _: candidate.has_airport
            and (
                candidate.has_international_airport
                or city.has_international_airport
                or candidate.key in international_keys
            ),
        )
        for candidate in extra_neighbors:
            edges.add((city.key, candidate.key))

        if city.name in NATIONAL_AIR_HUBS:
            for candidate in _pick_neighbors(
                city,
                neighbors,
                min_distance=250,
                max_distance=5000,
                max_count=8,
                predicate=lambda candidate, _: candidate.has_airport,
            ):
                edges.add((city.key, candidate.key))

    edges = add_forced_edges(merge_bidirectional(edges), city_by_name, "plane")
    indexed = {city.key: city for city in cities}
    return [(indexed[origin], indexed[destination]) for origin, destination in sorted(edges)]


def weighted_mode_pick(available_modes: list[str], weights: dict[str, int], rng: random.Random) -> str | None:
    if not available_modes:
        return None
    total_weight = sum(max(1, weights.get(mode, 1)) for mode in available_modes)
    pivot = rng.uniform(0, total_weight)
    progress = 0.0
    for mode in available_modes:
        progress += max(1, weights.get(mode, 1))
        if pivot <= progress:
            return mode
    return available_modes[-1]


def random_departure_datetime(
    mode: str,
    start_date: datetime,
    end_date: datetime,
    rng: random.Random,
) -> datetime:
    delta_days = max((end_date.date() - start_date.date()).days, 0)
    day_offset = rng.randint(0, delta_days) if delta_days else 0
    base_date = start_date.date() + timedelta(days=day_offset)
    hour = rng.choice(HOUR_WINDOWS.get(mode, HOUR_WINDOWS["bus"]))
    minute = rng.choice(MINUTES)
    return datetime(base_date.year, base_date.month, base_date.day, hour, minute)


def seasonal_factor_for(date_value: datetime) -> float:
    if date_value.month in {6, 7, 8}:
        return 1.14
    if date_value.month in {12, 1}:
        return 1.09
    return 1.0


def hub_factor_for(mode: str, origin: City, destination: City) -> float:
    if mode == "plane":
        if origin.has_international_airport and destination.has_international_airport:
            return 0.94
        if origin.has_airport and destination.has_airport:
            return 0.98
        return 1.08

    if mode == "train":
        if origin.is_rail_hub and destination.is_rail_hub:
            return 0.95
        return 1.03

    if mode == "bus":
        if origin.is_bus_hub and destination.is_bus_hub:
            return 0.96
        return 1.04

    return 1.0


def compute_distance_duration_price(
    mode: str,
    origin: City,
    destination: City,
    departure_at: datetime,
    rng: random.Random,
) -> tuple[float, int, int, dict]:
    base_distance = max(haversine_km(origin, destination), 8.0)
    season_factor = seasonal_factor_for(departure_at)
    hub_factor = hub_factor_for(mode, origin, destination)

    if mode == "plane":
        route_distance = base_distance * rng.uniform(1.02, 1.10)
        cruise_speed = rng.uniform(680, 820)
        flight_minutes = int((route_distance / cruise_speed) * 60)
        duration_min = max(55, flight_minutes + rng.randint(35, 95))
        price = max(2200, int(route_distance * rng.uniform(6.0, 8.8) * season_factor * hub_factor))
    elif mode == "train":
        route_distance = base_distance * rng.uniform(1.08, 1.35)
        min_duration = int((route_distance / 95.0) * 60)
        max_duration = int((route_distance / 45.0) * 60)
        max_duration = min(max_duration, int((base_distance * 1.35 / 50.0) * 60) + 120)
        duration_min = max(min_duration + 10, rng.randint(min_duration + 10, max_duration + 20))
        price = max(500, int(route_distance * rng.uniform(1.7, 3.2) * season_factor * hub_factor))
    elif mode == "electric_train":
        route_distance = min(base_distance * rng.uniform(1.05, 1.20), 250)
        min_duration = int((route_distance / 65.0) * 60)
        max_duration = int((route_distance / 30.0) * 60)
        duration_min = max(35, rng.randint(min_duration + 8, max_duration + 15))
        price = max(120, int(route_distance * rng.uniform(0.7, 1.4) * season_factor))
    else:
        route_distance = base_distance * rng.uniform(1.10, 1.45)
        min_duration = int((route_distance / 70.0) * 60)
        max_duration = int((route_distance / 35.0) * 60)
        duration_min = max(40, rng.randint(min_duration + 10, max_duration + 20))
        price = max(250, int(route_distance * rng.uniform(1.2, 2.4) * season_factor * hub_factor))

    return (
        route_distance,
        duration_min,
        price,
        {
            "base_distance_km": round(base_distance, 1),
            "hub_factor": round(hub_factor, 3),
            "seasonal_factor": round(season_factor, 3),
        },
    )


def choose_company(
    mode: str,
    from_city: City,
    carriers_by_mode: dict[str, list[CarrierDocument]],
    rng: random.Random,
) -> CarrierDocument:
    candidates = list(carriers_by_mode.get(mode) or [])
    if not candidates:
        raise ValueError(f"No carriers configured for mode {mode}.")

    if mode == "bus":
        same_region = [
            operator
            for operator in candidates
            if operator.metadata.get("region") == from_city.region
        ]
        candidates = same_region or candidates

    candidates.sort(key=lambda item: item.code)
    return rng.choice(candidates)


def _write_json_ticket_stream_array(out_path: Path, base_meta: dict, jsonl_path: Path, carrier_name: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("r", encoding="utf-8") as source, out_path.open("w", encoding="utf-8") as out:
        out.write("{\n")
        meta = {key: value for key, value in base_meta.items() if key != "tickets"}
        meta.setdefault("id", out_path.stem)
        meta.setdefault("company", carrier_name)
        meta_items = list(meta.items())
        for index, (key, value) in enumerate(meta_items):
            comma = "," if index < len(meta_items) - 1 else ","
            out.write(f"  {json.dumps(key, ensure_ascii=False)}: {json.dumps(value, ensure_ascii=False)}{comma}\n")
        out.write('  "tickets": [\n')
        first = True
        for line in source:
            line = line.strip()
            if not line:
                continue
            dto = UnifiedTicketDTO.from_dict(json.loads(line))
            legacy_record = dto.to_legacy_record(carrier_name=carrier_name)
            if not first:
                out.write(",\n")
            out.write(f"    {json.dumps(legacy_record, ensure_ascii=False)}")
            first = False
        out.write("\n  ]\n}\n")


def generate_dataset(config: GenerationConfig, *, data_dir: Path) -> GenerationResult:
    rng = random.Random(config.seed)
    cities = load_cities(data_dir)
    city_by_name = {city.name.casefold(): city for city in cities}
    neighbors = sorted_neighbors(cities)

    bus_operators = load_bus_operators(data_dir)
    plane_docs = load_docs(data_dir / "planes", transport_type="plane")
    train_docs = load_docs(data_dir / "trains", transport_type="train")
    electric_docs = load_docs(data_dir / "commuter_trains", transport_type="electric_train")

    carriers_by_mode = {
        "plane": list(plane_docs.values()),
        "train": list(train_docs.values()),
        "bus": bus_operators,
        "electric_train": list(electric_docs.values()),
    }

    edges_by_mode = {
        "plane": build_plane_edges(cities, neighbors, city_by_name) if plane_docs else [],
        "train": build_train_edges(cities, neighbors, city_by_name) if train_docs else [],
        "bus": build_bus_edges(cities, neighbors, city_by_name) if bus_operators else [],
        "electric_train": build_electric_edges(cities, neighbors, city_by_name) if electric_docs else [],
    }

    selected_modes = tuple(sorted(set(config.transport_types or edges_by_mode.keys())))
    edges_by_mode = {
        mode: pairs
        for mode, pairs in edges_by_mode.items()
        if mode in selected_modes and pairs
    }
    carriers_by_mode = {
        mode: carriers
        for mode, carriers in carriers_by_mode.items()
        if mode in edges_by_mode
    }

    if not any(edges_by_mode.values()):
        raise RuntimeError("Нет транспортной сети для генерации билетов.")

    weights = config.weights or {
        "plane": 20,
        "train": 30,
        "bus": 40,
        "electric_train": 10,
    }

    batch_dir = config.tmp_dir / "generated" / config.batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    for stale_file in batch_dir.glob("*"):
        if stale_file.is_file():
            stale_file.unlink()

    file_paths: dict[tuple[str, str], Path] = {}
    handles = {}
    counts_by_transport: Counter[str] = Counter()
    counts_by_carrier: Counter[str] = Counter()
    pair_counter: Counter[tuple[str, tuple[str, str], tuple[str, str]]] = Counter()
    generated = 0
    pair_soft_limit = max(10, min(36, max(1, config.total // 150000)))
    forced_tickets_per_pair = max(16, min(54, max(1, config.total // 180000)))
    carriers_lookup = {
        (document.transport_type, document.code): document
        for documents in carriers_by_mode.values()
        for document in documents
    }

    def ensure_handle(mode: str, carrier_code: str) -> Path:
        key = (mode, carrier_code)
        if key not in handles:
            path = batch_dir / f"{mode}__{carrier_code}.jsonl"
            path.unlink(missing_ok=True)
            handles[key] = path.open("a", encoding="utf-8")
            file_paths[key] = path
        return file_paths[key]

    def append_ticket(mode: str, carrier_code: str, ticket: UnifiedTicketDTO) -> None:
        path = ensure_handle(mode, carrier_code)
        handles[(mode, carrier_code)].write(json.dumps(ticket.as_dict(), ensure_ascii=False) + "\n")
        file_paths[(mode, carrier_code)] = path

    def emit_ticket(mode: str, origin: City, destination: City, *, forced_corridor: bool) -> bool:
        nonlocal generated
        carrier = choose_company(mode, origin, carriers_by_mode, rng)
        departure_at = random_departure_datetime(mode, config.start_date, config.end_date, rng)
        route_distance, duration_min, price, generation_meta = compute_distance_duration_price(
            mode,
            origin,
            destination,
            departure_at,
            rng,
        )
        arrival_at = departure_at + timedelta(minutes=duration_min)
        route_signature = build_route_signature(
            from_city=origin.slug,
            to_city=destination.slug,
            carrier=carrier.code,
            transport_type=mode,
            is_direct=True,
        )
        generation_meta = {
            **generation_meta,
            "forced_corridor": forced_corridor,
        }
        dto_payload = {
            "from_city": origin.slug,
            "to_city": destination.slug,
            "carrier": carrier.code,
            "transport_type": mode,
            "departure_datetime": departure_at.isoformat(),
            "arrival_datetime": arrival_at.isoformat(),
            "duration_minutes": duration_min,
            "price": max(1, int(price)),
            "distance_km": max(1, int(round(route_distance))),
            "is_direct": True,
            "available_seats": DEFAULT_SEATS.get(mode, 32),
            "is_active": True,
            "generation_batch": config.batch_id,
            "route_signature": route_signature,
            "generation_meta": generation_meta,
        }
        dto = UnifiedTicketDTO(
            external_id=build_external_ticket_id(dto_payload),
            **dto_payload,
        )
        append_ticket(mode, carrier.code, dto)
        pair_counter[(mode, origin.key, destination.key)] += 1
        counts_by_transport[mode] += 1
        counts_by_carrier[carrier.code] += 1
        generated += 1
        return True

    try:
        for mode in sorted(edges_by_mode):
            pairs = edges_by_mode[mode]
            forced_edges = {
                (origin_name.casefold(), destination_name.casefold())
                for origin_name, destination_name in FORCED_ROUTE_PAIRS.get(mode, [])
            }
            for origin, destination in pairs:
                if generated >= config.total:
                    break
                if (origin.name.casefold(), destination.name.casefold()) not in forced_edges:
                    continue
                for _ in range(forced_tickets_per_pair):
                    if generated >= config.total:
                        break
                    emit_ticket(mode, origin, destination, forced_corridor=True)

        available_modes = sorted(edges_by_mode)
        attempts = 0
        while generated < config.total and attempts < config.total * 6:
            attempts += 1
            mode = weighted_mode_pick(available_modes, weights, rng)
            if not mode:
                break
            origin, destination = rng.choice(edges_by_mode[mode])
            pair_key = (mode, origin.key, destination.key)
            if pair_counter[pair_key] >= pair_soft_limit and rng.random() < 0.7:
                continue
            emit_ticket(mode, origin, destination, forced_corridor=False)
    finally:
        for handle in handles.values():
            handle.close()

    manifest_payload = {
        "batch_id": config.batch_id,
        "seed": config.seed,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "start_date": config.start_date.date().isoformat(),
        "end_date": config.end_date.date().isoformat(),
        "total_generated": generated,
        "counts_by_transport": dict(sorted(counts_by_transport.items())),
        "counts_by_carrier": dict(sorted(counts_by_carrier.items())),
        "files": [
            {
                "transport_type": mode,
                "carrier": carrier_code,
                "path": file_paths[(mode, carrier_code)].name,
            }
            for mode, carrier_code in sorted(file_paths)
        ],
    }
    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if config.materialize_json:
        for key in sorted(file_paths):
            mode, carrier_code = key
            carrier = carriers_lookup[(mode, carrier_code)]
            _write_json_ticket_stream_array(
                carrier.legacy_output_path,
                carrier.metadata,
                file_paths[key],
                carrier.name,
            )

    return GenerationResult(
        batch_id=config.batch_id,
        batch_dir=batch_dir,
        manifest_path=manifest_path,
        total_generated=generated,
        counts_by_transport=dict(sorted(counts_by_transport.items())),
        counts_by_carrier=dict(sorted(counts_by_carrier.items())),
    )
