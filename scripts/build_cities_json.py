#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "russia_cities.csv"
OUT_PATH = ROOT / "data" / "cities" / "cities.json"
PROFILES_PATH = ROOT / "data" / "cities" / "city_transport_profiles.json"

COMMUTER_REGIONS = {
    "Москва",
    "Московская область",
    "Санкт-Петербург",
    "Ленинградская область",
}

PROFILE_FIELDS = {
    "has_airport",
    "has_international_airport",
    "has_train_station",
    "has_bus_station",
    "has_commuter_station",
    "is_rail_hub",
    "is_bus_hub",
}


def parse_population(raw: str) -> int:
    raw = raw.strip() or "0"
    try:
        val = float(raw.replace(",", "."))
    except ValueError:
        return 0
    return int(val * 1000)


def infer_infrastructure(population: int, region: str) -> dict:
    has_bus = population >= 18_000
    has_train = population >= 45_000
    has_airport = population >= 320_000
    has_commuter = region in COMMUTER_REGIONS and population >= 35_000
    return {
        "has_airport": bool(has_airport),
        "has_international_airport": False,
        "has_train_station": bool(has_train),
        "has_bus_station": bool(has_bus),
        "has_commuter_station": bool(has_commuter),
        "is_rail_hub": False,
        "is_bus_hub": False,
    }


def load_transport_profiles() -> list[dict]:
    if not PROFILES_PATH.exists():
        return []

    payload = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", payload) if isinstance(payload, dict) else payload
    if not isinstance(profiles, list):
        raise ValueError("city_transport_profiles.json должен содержать массив profiles.")

    normalized_profiles: list[dict] = []
    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            raise ValueError(f"Профиль #{index} должен быть JSON-объектом.")

        name = str(profile.get("name", "")).strip()
        region = str(profile.get("region", "")).strip()
        if not name:
            raise ValueError(f"Профиль #{index} не содержит name.")

        unknown_fields = sorted(set(profile) - {"name", "region"} - PROFILE_FIELDS)
        if unknown_fields:
            raise ValueError(
                f"Профиль {name} содержит неизвестные поля: {', '.join(unknown_fields)}."
            )

        normalized_profiles.append(
            {
                "name": name,
                "region": region,
                **{
                    field: bool(profile[field])
                    for field in PROFILE_FIELDS
                    if field in profile
                },
            }
        )

    return normalized_profiles


def resolve_profiles(cities: list[dict], profiles: list[dict]) -> dict[tuple[str, str], dict]:
    name_counts = Counter(city["name"].casefold() for city in cities)
    exact_city_keys = {
        (city["name"].casefold(), city["region"].casefold()): city
        for city in cities
    }
    resolved: dict[tuple[str, str], dict] = {}

    for profile in profiles:
        name_key = profile["name"].casefold()
        region_value = profile.get("region", "")
        region_key = region_value.casefold()

        if region_value:
            target_key = (name_key, region_key)
            if target_key not in exact_city_keys:
                raise ValueError(
                    f"Профиль {profile['name']} ({region_value}) не найден в russia_cities.csv."
                )
        else:
            matches = [
                key for key in exact_city_keys if key[0] == name_key
            ]
            if not matches:
                raise ValueError(f"Профиль {profile['name']} не найден в russia_cities.csv.")
            if name_counts[name_key] > 1:
                raise ValueError(
                    f"Город {profile['name']} встречается несколько раз. Укажите region в профиле."
                )
            target_key = matches[0]

        if target_key in resolved:
            raise ValueError(
                f"Дублирующийся профиль для {profile['name']} ({profile.get('region') or exact_city_keys[target_key]['region']})."
            )

        resolved[target_key] = {
            field: value
            for field, value in profile.items()
            if field in PROFILE_FIELDS
        }

    return resolved


def apply_profile(infra: dict, profile: dict) -> dict:
    merged = {**infra, **profile}

    if merged.get("has_international_airport"):
        merged["has_airport"] = True
    if merged.get("has_commuter_station"):
        merged["has_train_station"] = True
    if merged.get("is_rail_hub"):
        merged["has_train_station"] = True
    if merged.get("is_bus_hub"):
        merged["has_bus_station"] = True

    return merged


def main() -> None:
    cities: list[dict] = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("city", "").strip()
            if not name:
                continue

            population = parse_population(row.get("population", "0"))
            lat = float(row.get("lat", "0") or 0)
            lon = float(row.get("lon", "0") or 0)
            region_name = row.get("region_name", "").strip()

            cities.append(
                {
                    "name": name,
                    "population": population,
                    "region": region_name,
                    "lat": lat,
                    "lon": lon,
                }
            )

    profiles = load_transport_profiles()
    resolved_profiles = resolve_profiles(cities, profiles)

    enriched_cities = []
    for city in cities:
        city_key = (city["name"].casefold(), city["region"].casefold())
        infra = infer_infrastructure(city["population"], city["region"])
        profile = resolved_profiles.get(city_key, {})
        city_doc = {
            **city,
            **apply_profile(infra, profile),
        }
        enriched_cities.append(city_doc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_doc = {
        "meta": {
            "schema_version": 2,
            "source_hint": "russia_cities.csv + city_transport_profiles.json",
            "cities_count": len(enriched_cities),
            "transport_profiles_count": len(profiles),
            "note": (
                "Базовые флаги вычислены эвристически по населению и региону, "
                "после чего уточнены отдельным ручным справочником транспортных профилей."
            ),
        },
        "cities": enriched_cities,
    }
    OUT_PATH.write_text(
        json.dumps(out_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"OK: записано {len(enriched_cities)} городов в {OUT_PATH} "
        f"(ручных профилей: {len(profiles)})"
    )


if __name__ == "__main__":
    main()
