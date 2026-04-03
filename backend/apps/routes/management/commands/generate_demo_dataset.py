import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand

from apps.common.io import resolve_data_path


DEFAULT_DAYS = 365
DEFAULT_START_DATE = "2026-04-10"
BUS_NEIGHBORS = 4
TRAIN_NEIGHBORS = 3
ELECTRIC_TRAIN_NEIGHBORS = 2
PLANE_HUB_COUNT = 26
PLANE_HUB_NEIGHBORS = 8
PLANE_REGIONAL_HUB_LINKS = 4
NATIONAL_HUBS = {
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
}

AIRPORT_SPECIAL_CITIES = {
    "Анадырь",
    "Архангельск",
    "Астрахань",
    "Барнаул",
    "Белгород",
    "Благовещенск",
    "Владивосток",
    "Владикавказ",
    "Волгоград",
    "Воронеж",
    "Грозный",
    "Екатеринбург",
    "Ижевск",
    "Иркутск",
    "Казань",
    "Калининград",
    "Кемерово",
    "Краснодар",
    "Красноярск",
    "Магадан",
    "Махачкала",
    "Минеральные Воды",
    "Москва",
    "Мурманск",
    "Нальчик",
    "Нарьян-Мар",
    "Нижневартовск",
    "Нижнекамск",
    "Нижний Новгород",
    "Новосибирск",
    "Новый Уренгой",
    "Норильск",
    "Омск",
    "Оренбург",
    "Пермь",
    "Петрозаводск",
    "Петропавловск-Камчатский",
    "Ростов-на-Дону",
    "Самара",
    "Салехард",
    "Санкт-Петербург",
    "Саранск",
    "Саратов",
    "Сочи",
    "Ставрополь",
    "Сургут",
    "Сыктывкар",
    "Томск",
    "Тюмень",
    "Улан-Удэ",
    "Уфа",
    "Хабаровск",
    "Ханты-Мансийск",
    "Чебоксары",
    "Челябинск",
    "Чита",
    "Южно-Сахалинск",
    "Якутск",
    "Ярославль",
}

ELECTRIC_TRAIN_SPECIAL_CITIES = {
    "Барнаул",
    "Владивосток",
    "Волгоград",
    "Воронеж",
    "Екатеринбург",
    "Иркутск",
    "Казань",
    "Краснодар",
    "Красноярск",
    "Москва",
    "Нижний Новгород",
    "Новосибирск",
    "Омск",
    "Пермь",
    "Ростов-на-Дону",
    "Самара",
    "Санкт-Петербург",
    "Саратов",
    "Томск",
    "Тюмень",
    "Уфа",
    "Челябинск",
    "Ярославль",
}

BUS_SLOTS = (time(5, 50), time(9, 20), time(13, 40), time(17, 25), time(21, 10))
TRAIN_SLOTS = (time(6, 10), time(12, 35), time(19, 15))
ELECTRIC_TRAIN_SLOTS = (time(7, 5), time(13, 15), time(18, 10))
PLANE_SLOTS = (time(7, 50), time(10, 20), time(16, 35))
PLANE_HUB_SLOTS = (time(8, 15), time(12, 5), time(15, 10), time(20, 5))
LAST_SYNCED_AT = "2026-04-02T09:00:00"

PLANE_FILES = {
    "s7": "s7.json",
    "pobeda": "pobeda.json",
    "aeroflot": "aeroflot.json",
    "aviasales": "aviasales.json",
}

FORCED_ROUTE_PAIRS = {
    "bus": [
        ("Новосибирск", "Томск"),
        ("Новосибирск", "Барнаул"),
        ("Новосибирск", "Кемерово"),
        ("Томск", "Кемерово"),
        ("Москва", "Тула"),
        ("Москва", "Ярославль"),
        ("Санкт-Петербург", "Великий Новгород"),
        ("Владивосток", "Находка"),
    ],
    "train": [
        ("Новосибирск", "Томск"),
        ("Новосибирск", "Омск"),
        ("Новосибирск", "Красноярск"),
        ("Новосибирск", "Барнаул"),
        ("Москва", "Санкт-Петербург"),
        ("Москва", "Казань"),
        ("Москва", "Екатеринбург"),
        ("Владивосток", "Хабаровск"),
        ("Иркутск", "Улан-Удэ"),
    ],
    "electric_train": [
        ("Новосибирск", "Томск"),
        ("Москва", "Тула"),
        ("Москва", "Ярославль"),
        ("Санкт-Петербург", "Великий Новгород"),
    ],
    "plane": [
        ("Новосибирск", "Томск"),
        ("Новосибирск", "Владивосток"),
        ("Новосибирск", "Москва"),
        ("Новосибирск", "Санкт-Петербург"),
        ("Новосибирск", "Екатеринбург"),
        ("Новосибирск", "Красноярск"),
        ("Новосибирск", "Иркутск"),
        ("Новосибирск", "Хабаровск"),
        ("Новосибирск", "Казань"),
        ("Владивосток", "Москва"),
        ("Владивосток", "Санкт-Петербург"),
    ],
}


class Command(BaseCommand):
    help = "Generate a large Russia-wide demo dataset of cities and tickets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cities-source",
            default="data/russia_cities.csv",
            help="CSV file with all Russian cities.",
        )
        parser.add_argument(
            "--output",
            default="data/generated",
            help="Destination directory for generated demo data.",
        )
        parser.add_argument(
            "--start-date",
            default=DEFAULT_START_DATE,
            help="Start date for generated tickets in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_DAYS,
            help="How many days of tickets to generate.",
        )

    def handle(self, *args, **options):
        start_date = date.fromisoformat(options["start_date"])
        days = max(int(options["days"]), 1)
        source_path = resolve_data_path(options["cities_source"])
        output_dir = resolve_data_path(options["output"])
        output_dir.mkdir(parents=True, exist_ok=True)
        tickets_output_dir = output_dir / "tickets"
        tickets_output_dir.mkdir(parents=True, exist_ok=True)

        self._loaded_cities = self._load_cities(source_path)
        self._city_by_short_name = {
            city["short_name"]: city for city in self._loaded_cities
        }
        connections = self._build_connections(self._loaded_cities)
        tickets_by_file = self._build_tickets(connections, start_date, days)

        (output_dir / "cities.json").write_text(
            json.dumps(
                [self._city_payload(city) for city in self._loaded_cities],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        total_tickets = 0
        for file_name, payload in sorted(tickets_by_file.items()):
            total_tickets += len(payload)
            (tickets_output_dir / file_name).write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Generated Russia-wide demo dataset: "
                f"{len(self._loaded_cities)} cities, {total_tickets} tickets."
            )
        )

    def _load_cities(self, source_path):
        with source_path.open(encoding="utf-8") as source_file:
            rows = list(csv.DictReader(source_file))

        duplicate_counts = Counter(row["city"] for row in rows)
        cities = []
        for index, row in enumerate(rows, start=1):
            short_name = row["city"].strip()
            region_name = row["region_name"].strip()
            population_thousands = float(row["population"] or 0)
            name = (
                short_name
                if duplicate_counts[short_name] == 1
                else f"{short_name}, {region_name}"
            )
            cities.append(
                {
                    "name": name,
                    "short_name": short_name,
                    "slug": f"ru-city-{index:04d}",
                    "latitude": round(float(row["lat"]), 6),
                    "longitude": round(float(row["lon"]), 6),
                    "population_thousands": population_thousands,
                    "region_name": region_name,
                    "region_iso_code": row["region_iso_code"].strip(),
                    "federal_district": row["federal_district"].strip(),
                    "has_bus_station": True,
                    "has_airport": self._has_airport(short_name, population_thousands),
                    "has_train_station": population_thousands >= 18.0,
                    "has_commuter_station": self._has_electric_train(
                        short_name,
                        population_thousands,
                    ),
                }
            )

        return cities

    def _city_payload(self, city):
        return {
            "name": city["name"],
            "slug": city["slug"],
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "has_bus_station": city["has_bus_station"],
            "has_airport": city["has_airport"],
            "has_train_station": city["has_train_station"],
            "has_commuter_station": city["has_commuter_station"],
        }

    def _has_airport(self, short_name, population_thousands):
        return short_name in AIRPORT_SPECIAL_CITIES or population_thousands >= 140.0

    def _has_electric_train(self, short_name, population_thousands):
        return (
            short_name in ELECTRIC_TRAIN_SPECIAL_CITIES
            or population_thousands >= 130.0
        )

    def _build_connections(self, cities):
        distances = {
            city["slug"]: self._sorted_neighbors(city, cities)
            for city in cities
        }

        hubs = sorted(
            [city for city in cities if city["has_airport"]],
            key=lambda item: item["population_thousands"],
            reverse=True,
        )[:PLANE_HUB_COUNT]
        hub_slugs = {city["slug"] for city in hubs}
        national_hub_slugs = {
            city["slug"] for city in cities if city["name"] in NATIONAL_HUBS
        }

        return {
            "bus": self._finalize_edges(
                self._build_bus_edges(cities, distances),
                transport_type="bus",
            ),
            "train": self._finalize_edges(
                self._build_train_edges(cities, distances),
                transport_type="train",
            ),
            "electric_train": self._finalize_edges(
                self._build_electric_train_edges(cities, distances),
                transport_type="electric_train",
            ),
            "plane": self._finalize_edges(
                self._build_plane_edges(
                    cities,
                    distances,
                    hub_slugs,
                    national_hub_slugs,
                ),
                transport_type="plane",
            ),
        }

    def _finalize_edges(self, edges, *, transport_type):
        bidirectional_edges = set(edges)
        bidirectional_edges.update((to_slug, from_slug) for from_slug, to_slug in edges)
        bidirectional_edges.update(self._forced_edges(transport_type))
        return bidirectional_edges

    def _forced_edges(self, transport_type):
        edges = set()
        for from_name, to_name in FORCED_ROUTE_PAIRS.get(transport_type, []):
            origin = self._city_by_short_name.get(from_name)
            destination = self._city_by_short_name.get(to_name)
            if not origin or not destination:
                continue
            edges.add((origin["slug"], destination["slug"]))
            edges.add((destination["slug"], origin["slug"]))
        return edges

    def _sorted_neighbors(self, city, cities):
        neighbors = []
        for other in cities:
            if other["slug"] == city["slug"]:
                continue
            neighbors.append((self._distance_km(city, other), other))
        neighbors.sort(key=lambda item: item[0])
        return neighbors

    def _build_bus_edges(self, cities, distances):
        edges = set()
        for city in cities:
            max_distance = 260 if city["population_thousands"] >= 90 else 220
            neighbors = self._pick_neighbors(
                distances[city["slug"]],
                max_count=BUS_NEIGHBORS,
                min_distance=25,
                max_distance=max_distance,
                predicate=lambda other, distance: (
                    other["federal_district"] == city["federal_district"]
                    or other["region_name"] == city["region_name"]
                ),
            )
            if len(neighbors) < BUS_NEIGHBORS:
                fallback = self._pick_neighbors(
                    distances[city["slug"]],
                    max_count=BUS_NEIGHBORS,
                    min_distance=25,
                    max_distance=max_distance,
                )
                neighbors = self._merge_neighbors(neighbors, fallback, BUS_NEIGHBORS)

            for _, target in neighbors:
                edges.add((city["slug"], target["slug"]))
        return edges

    def _build_train_edges(self, cities, distances):
        edges = set()
        rail_slugs = {
            city["slug"] for city in cities if city["has_train_station"]
        }
        for city in cities:
            if city["slug"] not in rail_slugs:
                continue
            neighbors = self._pick_neighbors(
                distances[city["slug"]],
                max_count=TRAIN_NEIGHBORS,
                min_distance=80,
                max_distance=900,
                predicate=lambda other, distance: (
                    other["slug"] in rail_slugs
                    and (
                        other["federal_district"] == city["federal_district"]
                        or other["population_thousands"] >= 200
                    )
                ),
            )
            if len(neighbors) < TRAIN_NEIGHBORS:
                fallback = self._pick_neighbors(
                    distances[city["slug"]],
                    max_count=TRAIN_NEIGHBORS,
                    min_distance=80,
                    max_distance=900,
                    predicate=lambda other, distance: other["slug"] in rail_slugs,
                )
                neighbors = self._merge_neighbors(neighbors, fallback, TRAIN_NEIGHBORS)

            for _, target in neighbors:
                edges.add((city["slug"], target["slug"]))
        return edges

    def _build_electric_train_edges(self, cities, distances):
        edges = set()
        for city in cities:
            if not city["has_commuter_station"]:
                continue
            neighbors = self._pick_neighbors(
                distances[city["slug"]],
                max_count=ELECTRIC_TRAIN_NEIGHBORS,
                min_distance=20,
                max_distance=170,
                predicate=lambda other, distance: other["has_commuter_station"],
            )
            for _, target in neighbors:
                edges.add((city["slug"], target["slug"]))
        return edges

    def _build_plane_edges(self, cities, distances, hub_slugs, national_hub_slugs):
        edges = set()
        for city in cities:
            if not city["has_airport"]:
                continue

            for _, target in self._pick_neighbors(
                distances[city["slug"]],
                max_count=len(national_hub_slugs),
                min_distance=250,
                max_distance=5500,
                predicate=lambda other, distance: other["slug"] in national_hub_slugs,
            ):
                edges.add((city["slug"], target["slug"]))

            if city["slug"] in hub_slugs:
                neighbors = self._pick_neighbors(
                    distances[city["slug"]],
                    max_count=PLANE_HUB_NEIGHBORS,
                    min_distance=250,
                    max_distance=4500,
                    predicate=lambda other, distance: other["slug"] in hub_slugs,
                )
            else:
                neighbors = self._pick_neighbors(
                    distances[city["slug"]],
                    max_count=PLANE_REGIONAL_HUB_LINKS,
                    min_distance=250,
                    max_distance=4500,
                    predicate=lambda other, distance: other["slug"] in hub_slugs,
                )

            for _, target in neighbors:
                edges.add((city["slug"], target["slug"]))
        return edges

    def _pick_neighbors(
        self,
        sorted_neighbors,
        *,
        max_count,
        min_distance=0,
        max_distance=None,
        predicate=None,
    ):
        picked = []
        for distance, other in sorted_neighbors:
            if distance < min_distance:
                continue
            if max_distance is not None and distance > max_distance:
                continue
            if predicate and not predicate(other, distance):
                continue
            picked.append((distance, other))
            if len(picked) == max_count:
                break
        return picked

    def _merge_neighbors(self, primary, fallback, limit):
        merged = list(primary)
        seen = {item[1]["slug"] for item in primary}
        for item in fallback:
            if item[1]["slug"] in seen:
                continue
            merged.append(item)
            seen.add(item[1]["slug"])
            if len(merged) == limit:
                break
        return merged

    def _build_tickets(self, connections, start_date, days):
        tickets_by_file = defaultdict(list)
        counters = defaultdict(int)
        city_lookup = {city["slug"]: city for city in self._loaded_cities}

        for offset in range(days):
            current_date = start_date + timedelta(days=offset)
            self._append_mode_tickets(
                city_lookup,
                tickets_by_file,
                counters,
                connections["bus"],
                current_date,
                carrier_code="bus_companies",
                slots=BUS_SLOTS,
                transport_type="bus",
            )
            self._append_mode_tickets(
                city_lookup,
                tickets_by_file,
                counters,
                connections["train"],
                current_date,
                carrier_code="rzd",
                slots=TRAIN_SLOTS,
                transport_type="train",
            )
            self._append_mode_tickets(
                city_lookup,
                tickets_by_file,
                counters,
                connections["electric_train"],
                current_date,
                carrier_code="rzd",
                slots=ELECTRIC_TRAIN_SLOTS,
                transport_type="electric_train",
            )
            self._append_mode_tickets(
                city_lookup,
                tickets_by_file,
                counters,
                connections["plane"],
                current_date,
                carrier_code=None,
                slots=PLANE_SLOTS,
                transport_type="plane",
            )

        return tickets_by_file

    def _append_mode_tickets(
        self,
        city_lookup,
        tickets_by_file,
        counters,
        edges,
        current_date,
        *,
        carrier_code,
        slots,
        transport_type,
    ):
        for from_slug, to_slug in sorted(edges):
            origin = city_lookup[from_slug]
            destination = city_lookup[to_slug]
            distance_km = max(30, round(self._distance_km(origin, destination)))

            edge_slots = slots
            selected_carrier_code = carrier_code
            if transport_type == "plane":
                selected_carrier_code, edge_slots = self._plane_schedule_for_edge(
                    origin,
                    destination,
                )

            for slot in edge_slots:
                departure = datetime.combine(current_date, slot)
                arrival = departure + timedelta(
                    minutes=self._duration_minutes(transport_type, distance_km)
                )
                counters[selected_carrier_code] += 1
                tickets_by_file[self._carrier_file(selected_carrier_code)].append(
                    {
                        "external_id": self._external_id(
                            selected_carrier_code,
                            counters[selected_carrier_code],
                        ),
                        "carrier_code": selected_carrier_code,
                        "from_city": origin["name"],
                        "to_city": destination["name"],
                        "transport_type": transport_type,
                        "departure_datetime": departure.isoformat(),
                        "arrival_datetime": arrival.isoformat(),
                        "price": self._price(transport_type, distance_km),
                        "distance_km": distance_km,
                        "is_direct": True,
                        "available_seats": self._available_seats(
                            transport_type,
                            origin,
                            destination,
                        ),
                        "is_active": True,
                        "last_synced_at": LAST_SYNCED_AT,
                    }
                )

    def _plane_schedule_for_edge(self, origin, destination):
        carrier_pool = ["s7", "pobeda", "aeroflot", "aviasales"]
        carrier_code = carrier_pool[
            (abs(hash(origin["slug"])) + abs(hash(destination["slug"]))) % len(carrier_pool)
        ]
        is_hub_pair = (
            origin["population_thousands"] >= 800
            and destination["population_thousands"] >= 800
        )
        slots = PLANE_HUB_SLOTS if is_hub_pair else PLANE_SLOTS
        return carrier_code, slots

    def _carrier_file(self, carrier_code):
        if carrier_code == "rzd":
            return "rzd.json"
        if carrier_code == "bus_companies":
            return "buses.json"
        return PLANE_FILES[carrier_code]

    def _external_id(self, carrier_code, counter):
        prefixes = {
            "s7": "S7",
            "pobeda": "POB",
            "aeroflot": "AFL",
            "aviasales": "AVS",
            "rzd": "RZD",
            "bus_companies": "BUS",
        }
        return f"{prefixes[carrier_code]}-{counter:06d}"

    def _duration_minutes(self, transport_type, distance_km):
        if transport_type == "bus":
            return max(45, round(distance_km / 58 * 60 + 20))
        if transport_type == "train":
            return max(60, round(distance_km / 72 * 60 + 25))
        if transport_type == "electric_train":
            return max(40, round(distance_km / 50 * 60 + 15))
        return max(75, round(distance_km / 680 * 60 + 85))

    def _price(self, transport_type, distance_km):
        if transport_type == "bus":
            return max(350, round(distance_km * 3.4 + 180))
        if transport_type == "train":
            return max(700, round(distance_km * 2.9 + 420))
        if transport_type == "electric_train":
            return max(250, round(distance_km * 2.1 + 120))
        return max(2800, round(distance_km * 5.8 + 2400))

    def _available_seats(self, transport_type, origin, destination):
        if transport_type == "bus":
            return 18 + ((len(origin["slug"]) + len(destination["slug"])) % 22)
        if transport_type in {"train", "electric_train"}:
            return 40 + ((len(origin["slug"]) + len(destination["slug"])) % 120)
        return 6 + ((len(origin["slug"]) + len(destination["slug"])) % 55)

    def _distance_km(self, origin, destination):
        lat1 = math.radians(origin["latitude"])
        lon1 = math.radians(origin["longitude"])
        lat2 = math.radians(destination["latitude"])
        lon2 = math.radians(destination["longitude"])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return 6371.0 * c
