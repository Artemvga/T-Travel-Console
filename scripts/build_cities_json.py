#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "russia_cities.csv"
OUT_PATH = ROOT / "data" / "cities" / "cities.json"


def parse_population(raw: str) -> int:
    raw = raw.strip() or "0"
    try:
        val = float(raw.replace(",", "."))
    except ValueError:
        return 0
    # В CSV значения в тыс. человек (типа 632.4), умножаем на 1000
    return int(val * 1000)


def infer_infrastructure(population: int, region: str) -> dict:
    has_bus = population >= 20_000
    has_train = population >= 50_000
    has_airport = population >= 300_000
    has_commuter = region in {
        "Московская область",
        "Москва",
        "Ленинградская область",
        "Санкт-Петербург",
    } and population >= 30_000
    return {
        "has_airport": bool(has_airport),
        "has_train_station": bool(has_train),
        "has_bus_station": bool(has_bus),
        "has_commuter_station": bool(has_commuter),
    }


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

            infra = infer_infrastructure(population, region_name)
            city_doc = {
                "name": name,
                "population": population,
                "region": region_name,
                "lat": lat,
                "lon": lon,
                **infra,
            }
            cities.append(city_doc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_doc = {
        "meta": {
            "schema_version": 1,
            "source_hint": "russia_cities.csv",
            "cities_count": len(cities),
            "note": "Инфраструктура определена эвристически по населению и региону, потом можно дообогатить по API",
        },
        "cities": cities,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, ensure_ascii=False, indent=2)

    print(f"OK: записано {len(cities)} городов в {OUT_PATH}")


if __name__ == "__main__":
    main()

