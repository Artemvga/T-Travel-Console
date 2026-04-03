#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


@dataclass(frozen=True)
class City:
    name: str
    lat: float
    lon: float
    region: str
    has_airport: bool
    has_train_station: bool
    has_bus_station: bool


def load_cities() -> list[City]:
    with open(DATA / "cities" / "cities.json", "r", encoding="utf-8") as f:
        doc = json.load(f)
    out: list[City] = []
    for c in doc.get("cities", []):
        out.append(
            City(
                name=c["name"],
                lat=float(c["lat"]),
                lon=float(c["lon"]),
                region=c.get("region", ""),
                has_airport=bool(c.get("has_airport", False)),
                has_train_station=bool(c.get("has_train_station", False)),
                has_bus_station=bool(c.get("has_bus_station", False)),
            )
        )
    return out


def load_plane_docs() -> dict[str, dict]:
    plane_dir = DATA / "planes"
    res: dict[str, dict] = {}
    for slug in ["aeroflot", "s7", "pobeda"]:
        p = plane_dir / f"{slug}.json"
        if p.exists():
            res[slug] = json.loads(p.read_text(encoding="utf-8"))
    return res


def load_train_doc() -> dict:
    p = DATA / "trains" / "rzd.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_bus_operators() -> list[dict]:
    idx_path = DATA / "buses" / "operators_index.json"
    if not idx_path.exists():
        return []
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    return idx.get("operators", [])


def haversine_km(a: City, b: City) -> float:
    r = 6371.0
    lat1 = math.radians(a.lat)
    lon1 = math.radians(a.lon)
    lat2 = math.radians(b.lat)
    lon2 = math.radians(b.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    days = max(delta.days, 0)
    offset_days = random.randint(0, days)
    return start + timedelta(days=offset_days)


def random_time_for_mode(mode: str) -> tuple[int, int]:
    r = random.random()
    if mode == "plane":
        if r < 0.4:
            hour = random.randint(6, 10)
        elif r < 0.8:
            hour = random.randint(11, 17)
        else:
            hour = random.randint(18, 22)
    elif mode == "train":
        if r < 0.3:
            hour = random.randint(6, 11)
        elif r < 0.7:
            hour = random.randint(12, 19)
        else:
            hour = random.randint(20, 23)
    else:
        if r < 0.5:
            hour = random.randint(6, 11)
        elif r < 0.9:
            hour = random.randint(12, 19)
        else:
            hour = random.randint(5, 7)
    minute = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return hour, minute


def gen_ticket(from_city: City, to_city: City, company: str, mode: str, base_date_start: datetime, base_date_end: datetime) -> dict:
    base_d = max(haversine_km(from_city, to_city), 10.0)

    # Эмуляция кривизны: реальный маршрут часто длиннее прямой линии
    if mode == "plane":
        factor = random.uniform(1.02, 1.08)
        avg_speed = 750.0
        price_per_km = 7.0
        min_price = 2500
    elif mode == "train":
        factor = random.uniform(1.05, 1.2)
        avg_speed = 80.0
        price_per_km = 2.5
        min_price = 400
    else:
        factor = random.uniform(1.05, 1.25)
        avg_speed = 60.0
        price_per_km = 1.8
        min_price = 200

    d = base_d * factor
    date = random_date(base_date_start, base_date_end)
    hour, minute = random_time_for_mode(mode)

    duration_hours = d / avg_speed
    duration_min = int(duration_hours * 60) + random.randint(-15, 30)
    duration_min = max(duration_min, 30)

    price = int(d * price_per_km * random.uniform(0.8, 1.3))
    price = max(price, min_price)

    return {
        "from_city": from_city.name,
        "to_city": to_city.name,
        "company": company,
        "departure_date": date.strftime("%Y-%m-%d"),
        "departure_time": f"{hour:02d}:{minute:02d}",
        "price_rub": price,
        "distance_km": round(d, 1),
        "duration_min": duration_min,
        "mode": mode,
    }


def weighted_pick_mode(available: dict[str, list], mode_weights: dict[str, int]) -> str | None:
    # available keys: plane/train/bus with non-empty lists
    pool: list[tuple[str, int]] = []
    for m, lst in available.items():
        if lst:
            pool.append((m, mode_weights.get(m, 1)))
    if not pool:
        return None
    total_w = sum(w for _, w in pool)
    r = random.uniform(0, total_w)
    acc = 0.0
    for m, w in pool:
        acc += w
        if r <= acc:
            return m
    return pool[-1][0]


def write_json_ticket_stream_array(out_path: Path, base_meta: dict, jsonl_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tickets_written = 0

    # Собираем финальный JSON без загрузки всех билетов в память
    with open(jsonl_path, "r", encoding="utf-8") as inp, open(out_path, "w", encoding="utf-8") as out:
        out.write("{\n")
        meta_items = [(k, v) for k, v in base_meta.items()]
        for i, (k, v) in enumerate(meta_items):
            comma = "," if i < len(meta_items) - 1 else ","
            out.write(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}{comma}\n")

        out.write('  "tickets": [\n')
        first = True
        for line in inp:
            line = line.strip()
            if not line:
                continue
            ticket = json.loads(line)
            if not first:
                out.write(",\n")
            out.write("    " + json.dumps(ticket, ensure_ascii=False))
            first = False
            tickets_written += 1
        out.write("\n  ]\n")
        out.write("}\n")

    return


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Генерация билетов с записью в один JSON на компанию.")
    p.add_argument("--total", type=int, default=100_000, help="сколько билетов попытаться сгенерировать")
    p.add_argument("--bus-weight", type=int, default=45)
    p.add_argument("--train-weight", type=int, default=35)
    p.add_argument("--plane-weight", type=int, default=20)
    p.add_argument("--start-date", type=str, default="2026-04-10", help="дата старта (YYYY-MM-DD)")
    p.add_argument("--end-date", type=str, default="2026-12-31", help="дата конца (YYYY-MM-DD)")
    p.add_argument("--tmp-dir", type=str, default="data/_tmp_ticket_jsonl", help="временная папка для jsonl")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cities = load_cities()
    if len(cities) < 2:
        raise SystemExit("Недостаточно городов для генерации.")

    bus_ops = load_bus_operators()
    plane_docs = load_plane_docs()
    plane_slugs = list(plane_docs.keys())
    train_doc = load_train_doc()

    if not bus_ops and not plane_slugs and not train_doc:
        raise SystemExit("Нет компаний для генерации (bus/plane/train).")

    mode_weights = {"plane": args.plane_weight, "train": args.train_weight, "bus": args.bus_weight}

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

    plane_cities = [c for c in cities if c.has_airport]
    train_cities = [c for c in cities if c.has_train_station]
    bus_cities = [c for c in cities if c.has_bus_station]

    def build_region_map(items: list[City]) -> dict[str, list[City]]:
        m: dict[str, list[City]] = {}
        for c in items:
            m.setdefault(c.region, []).append(c)
        return m

    plane_by_region = build_region_map(plane_cities)
    train_by_region = build_region_map(train_cities)
    bus_by_region = build_region_map(bus_cities)

    # Открываем jsonl-файлы для потоковой записи
    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Очереди для билетов:
    # - автобус: один jsonl на operator.id
    # - авиа: один jsonl на slug
    # - поезд: один jsonl на "rzd"
    jsonl_files: dict[str, Path] = {}

    # bus
    for op in bus_ops:
        op_id = op["id"]
        jsonl_files[f"bus:{op_id}"] = tmp_dir / f"bus_{op_id}.jsonl"
        jsonl_files[f"bus:{op_id}"].unlink(missing_ok=True)

    # plane
    for slug in plane_slugs:
        jsonl_files[f"plane:{slug}"] = tmp_dir / f"plane_{slug}.jsonl"
        jsonl_files[f"plane:{slug}"].unlink(missing_ok=True)

    # train
    jsonl_files["train:rzd"] = tmp_dir / "train_rzd.jsonl"
    jsonl_files["train:rzd"].unlink(missing_ok=True)

    # Экземпляры открываем на лету: чтобы не держать много дескрипторов, можно открывать append по месту
    def append_ticket(key: str, ticket: dict) -> None:
        with open(jsonl_files[key], "a", encoding="utf-8") as f:
            f.write(json.dumps(ticket, ensure_ascii=False) + "\n")

    def pick_pair(mode: str, max_attempts: int = 80) -> tuple[City, City] | None:
        for _ in range(max_attempts):
            if mode == "plane":
                a = random.choice(plane_cities)
                if random.random() < 0.7:
                    same = [c for c in plane_by_region.get(a.region, []) if c.name != a.name]
                    b = random.choice(same) if same else random.choice(plane_cities)
                else:
                    b = random.choice(plane_cities)
                if b.name == a.name:
                    continue
                d = haversine_km(a, b)
                if d >= 250:
                    return a, b
            elif mode == "train":
                a = random.choice(train_cities)
                if random.random() < 0.7:
                    same = [c for c in train_by_region.get(a.region, []) if c.name != a.name]
                    b = random.choice(same) if same else random.choice(train_cities)
                else:
                    b = random.choice(train_cities)
                if b.name == a.name:
                    continue
                d = haversine_km(a, b)
                if 80 <= d <= 2000:
                    return a, b
            else:
                a = random.choice(bus_cities)
                if random.random() < 0.7:
                    same = [c for c in bus_by_region.get(a.region, []) if c.name != a.name]
                    b = random.choice(same) if same else random.choice(bus_cities)
                else:
                    b = random.choice(bus_cities)
                if b.name == a.name:
                    continue
                d = haversine_km(a, b)
                if d <= 1200:
                    return a, b
        return None

    seen_pairs: set[tuple[str, str, str]] = set()
    generated = 0
    attempts = 0

    while generated < args.total:
        attempts += 1
        available = {
            "plane": plane_cities if (plane_cities and plane_slugs) else [],
            "train": train_cities if (train_cities and train_doc) else [],
            "bus": bus_cities if (bus_cities and bus_ops) else [],
        }
        mode = weighted_pick_mode(available, mode_weights)
        if not mode:
            break

        pair = pick_pair(mode)
        if not pair:
            continue
        a, b = pair

        key = (mode, a.name, b.name)
        if key in seen_pairs and random.random() < 0.85:
            continue
        seen_pairs.add(key)

        if mode == "plane":
            slug = random.choice(plane_slugs)
            company = plane_docs[slug]["company"]
            ticket = gen_ticket(a, b, company, mode, start_date, end_date)
            append_ticket(f"plane:{slug}", ticket)
        elif mode == "train":
            company = train_doc.get("company", "РЖД")
            ticket = gen_ticket(a, b, company, mode, start_date, end_date)
            append_ticket("train:rzd", ticket)
        else:
            # оператор выбираем по региону города отправления (максимально правдоподобно)
            ops_same = [op for op in bus_ops if op.get("region") == a.region]
            op = random.choice(ops_same) if ops_same else random.choice(bus_ops)
            op_id = op["id"]
            company = op.get("company", "")
            ticket = gen_ticket(a, b, company, mode, start_date, end_date)
            append_ticket(f"bus:{op_id}", ticket)

        generated += 1

        # Сейв прогресса (коротко)
        if generated % 100000 == 0:
            print(f"progress: {generated}/{args.total}")

        if attempts > args.total * 50:
            # чтобы не зависнуть на невозможных условиях
            break

    print(f"OK: сгенерировано {generated} билетов. Сборка JSON по компаниям...")

    # Собираем итоговые JSON: один файл на компанию
    # bus
    for op in bus_ops:
        op_id = op["id"]
        jsonl_path = jsonl_files.get(f"bus:{op_id}")
        if not jsonl_path or not jsonl_path.exists():
            continue
        out_path = DATA / "buses" / "by_operator" / f"{op_id}.json"
        base_meta = {k: v for k, v in op.items() if k != "tickets"}
        write_json_ticket_stream_array(out_path, base_meta, jsonl_path)

    # planes
    for slug, doc in plane_docs.items():
        jsonl_path = jsonl_files.get(f"plane:{slug}")
        if not jsonl_path or not jsonl_path.exists():
            continue
        out_path = DATA / "planes" / f"{slug}.json"
        base_meta = {k: v for k, v in doc.items() if k != "tickets"}
        write_json_ticket_stream_array(out_path, base_meta, jsonl_path)

    # train
    if train_doc:
        jsonl_path = jsonl_files.get("train:rzd")
        out_path = DATA / "trains" / "rzd.json"
        base_meta = {k: v for k, v in train_doc.items() if k != "tickets"}
        if jsonl_path and jsonl_path.exists():
            write_json_ticket_stream_array(out_path, base_meta, jsonl_path)

    print("OK: финальные JSON по компаниям собраны.")


if __name__ == "__main__":
    main()

