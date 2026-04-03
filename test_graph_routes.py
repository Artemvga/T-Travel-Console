import json
from pathlib import Path

from graph_routes import TOP_ROUTES_LIMIT, TravelRouter, format_route


def pick_first_non_empty_plane_ticket() -> dict | None:
    root = Path(__file__).resolve().parent
    for slug in ["s7", "aeroflot", "pobeda"]:
        p = root / "data" / "planes" / f"{slug}.json"
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        tickets = doc.get("tickets", [])
        if tickets:
            return tickets[0]
    return None


def main() -> None:
    router = TravelRouter(
        "data/cities/cities.json",
        "data/buses/by_operator",
        "data/trains/rzd.json",
        "data/planes",
    )

    earliest_date = "2026-04-10"
    earliest_time = "00:00"

    ticket = pick_first_non_empty_plane_ticket()
    if not ticket:
        print("Нет тестовых билетов в data/planes (s7/aeroflot/pobeda).")
        return

    start = ticket["from_city"]
    end = ticket["to_city"]
    preferred = {ticket.get("company", "")}

    print(f"=== Smoke-test по одному сегменту: {start} -> {end} ===")
    print(f"Городов в базе: {router.total_cities}")

    print("\n1) Проверка существования прямого маршрута")
    print(
        f"{start} -> {end} (только прямой):",
        "Да"
        if router.route_exists(
            start, end, direct_only=True, earliest_date=earliest_date, earliest_time=earliest_time
        )
        else "Нет",
    )

    print("\n2) Маршруты (приоритет быстрее)")
    routes_fast = router.find_routes(
        start=start,
        end=end,
        direct_only=True,
        earliest_date=earliest_date,
        earliest_time=earliest_time,
        priority="fast",
        preferred_companies=preferred,
    )
    for idx, route in enumerate(routes_fast[:TOP_ROUTES_LIMIT], start=1):
        print(format_route(route, idx))


if __name__ == "__main__":
    main()

