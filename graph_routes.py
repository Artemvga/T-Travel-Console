import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from accounts import (
    add_favorite_route,
    canonical_username,
    is_admin,
    list_all_user_accounts,
    list_favorites,
    register_user,
    remove_favorite,
    verify_login,
)


TRANSPORT_RULES = {
    "bus": "has_bus_station",
    "train": "has_train_station",
    "flight": "has_airport",
}

TOP_ROUTES_LIMIT = 5

COMPANY_ALIASES = {
    "s7": "S7",
    "с7": "S7",
    "победа": "Победа",
    "aэрофлот": "Аэрофлот",
    "аэрофлот": "Аэрофлот",
    "ржд": "РЖД",
    "автовокзал": "Автовокзал",
}


@dataclass
class Segment:
    city_from: str
    city_to: str
    transport: str
    company: str
    price: int
    duration_min: int
    departure_date: str
    departure_time: str
    flight_number: str


def segment_departure_dt(seg: Segment) -> datetime:
    return datetime.strptime(f"{seg.departure_date} {seg.departure_time}", "%Y-%m-%d %H:%M")


def segment_arrival_dt(seg: Segment) -> datetime:
    return segment_departure_dt(seg) + timedelta(minutes=seg.duration_min)


@dataclass
class RouteOption:
    path: list[str]
    segments: list[Segment]
    total_price: int
    total_duration: int
    transfers: int
    preferred_hits: int


class TravelRouter:
    def __init__(self, cities_path: str, bus_path: str, train_path: str, flight_path: str):
        self.cities: dict[str, dict] = {}
        self.total_cities = 0
        self.graph: dict[str, list[Segment]] = {}
        self._load_data(cities_path, bus_path, train_path, flight_path)

    def _load_data(self, cities_path: str, bus_path: str, train_path: str, flight_path: str) -> None:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
        cities_list = cities_data.get("cities", [])
        self.total_cities = cities_data.get("total_cities", 0) or cities_data.get("meta", {}).get(
            "cities_count", 0
        ) or len(cities_list)
        for city in cities_list:
            self.cities[city["name"]] = city

        self.graph = {city_name: [] for city_name in self.cities}
        self._add_tickets_from_path(bus_path, "bus")
        self._add_tickets_from_path(train_path, "train")
        self._add_tickets_from_path(flight_path, "flight")

    def _add_tickets_from_path(self, path: str, transport: str) -> None:
        p = Path(path)
        if p.is_dir():
            for file_path in p.glob("*.json"):
                self._add_tickets_to_graph(str(file_path), transport)
        else:
            self._add_tickets_to_graph(path, transport)

    def _add_tickets_to_graph(self, file_path: str, transport: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for ticket in data.get("tickets", []):
            city_from = ticket.get("from_city", ticket.get("from"))
            city_to = ticket.get("to_city", ticket.get("to"))
            if not city_from or not city_to:
                continue

            if not self._city_supports_transport(city_from, transport):
                continue
            if not self._city_supports_transport(city_to, transport):
                continue

            fn = ticket.get("flight_number", "")
            price = ticket.get("price_rub", ticket.get("price"))
            duration_min = ticket.get("duration_min")
            departure_date = ticket.get("departure_date")
            departure_time = ticket.get("departure_time")
            if price is None or duration_min is None or not departure_date or not departure_time:
                continue

            company = ticket.get("company", "")

            segment = Segment(
                city_from=city_from,
                city_to=city_to,
                transport=transport,
                company=company,
                price=int(price),
                duration_min=int(duration_min),
                departure_date=departure_date,
                departure_time=departure_time,
                flight_number=fn,
            )

            reverse_segment = Segment(
                city_from=city_to,
                city_to=city_from,
                transport=transport,
                company=company,
                price=int(price),
                duration_min=int(duration_min),
                departure_date=departure_date,
                departure_time=departure_time,
                flight_number=fn,
            )
            self.graph[city_from].append(segment)
            self.graph[city_to].append(reverse_segment)

    def _city_supports_transport(self, city: str, transport: str) -> bool:
        if city not in self.cities:
            return False
        rule_field = TRANSPORT_RULES[transport]
        return bool(self.cities[city].get(rule_field, False))

    def route_exists(
        self,
        start: str,
        end: str,
        direct_only: bool,
        earliest_date: str,
        earliest_time: str = "00:00",
    ) -> bool:
        return (
            len(self.find_routes(start, end, direct_only, earliest_date, earliest_time, "optimal", set())) > 0
        )

    def find_routes(
        self,
        start: str,
        end: str,
        direct_only: bool,
        earliest_date: str,
        earliest_time: str,
        priority: str,
        preferred_companies: set[str],
    ) -> list[RouteOption]:
        if start not in self.graph or end not in self.graph or start == end:
            return []

        earliest_at_city = datetime.strptime(f"{earliest_date} {earliest_time}", "%Y-%m-%d %H:%M")

        max_legs = 1 if direct_only else 4
        collected: list[RouteOption] = []
        self._dfs_collect_routes(
            current=start,
            end=end,
            visited={start},
            current_segments=[],
            max_legs=max_legs,
            earliest_at_city=earliest_at_city,
            preferred_companies=preferred_companies,
            collected=collected,
        )
        return self._sort_routes(collected, priority)

    def _dfs_collect_routes(
        self,
        current: str,
        end: str,
        visited: set[str],
        current_segments: list[Segment],
        max_legs: int,
        earliest_at_city: datetime,
        preferred_companies: set[str],
        collected: list[RouteOption],
    ) -> None:
        if len(current_segments) > max_legs:
            return

        if current == end and current_segments:
            path = [current_segments[0].city_from] + [s.city_to for s in current_segments]
            total_price = sum(s.price for s in current_segments)
            total_duration = sum(s.duration_min for s in current_segments)
            transfers = len(current_segments) - 1
            preferred_hits = sum(1 for s in current_segments if s.company in preferred_companies)
            collected.append(
                RouteOption(
                    path=path,
                    segments=list(current_segments),
                    total_price=total_price,
                    total_duration=total_duration,
                    transfers=transfers,
                    preferred_hits=preferred_hits,
                )
            )
            return

        for segment in self.graph.get(current, []):
            dep = segment_departure_dt(segment)
            if dep < earliest_at_city:
                continue
            next_city = segment.city_to
            if next_city in visited:
                continue
            visited.add(next_city)
            current_segments.append(segment)
            arrival_here = segment_arrival_dt(segment)
            self._dfs_collect_routes(
                current=next_city,
                end=end,
                visited=visited,
                current_segments=current_segments,
                max_legs=max_legs,
                earliest_at_city=arrival_here,
                preferred_companies=preferred_companies,
                collected=collected,
            )
            current_segments.pop()
            visited.remove(next_city)

    def _sort_routes(self, routes: list[RouteOption], priority: str) -> list[RouteOption]:
        if priority == "fast":
            return sorted(routes, key=lambda x: (x.total_duration, x.total_price, x.transfers, -x.preferred_hits))
        if priority == "cheap":
            return sorted(routes, key=lambda x: (x.total_price, x.total_duration, x.transfers, -x.preferred_hits))
        return sorted(
            routes,
            key=lambda x: (x.total_price * 0.45 + x.total_duration * 0.45 + x.transfers * 120 - x.preferred_hits * 40),
        )

    @staticmethod
    def normalize_companies(raw_text: str) -> set[str]:
        if not raw_text.strip() or raw_text.strip().lower() == "all":
            return set()
        result = set()
        for item in raw_text.split(","):
            key = item.strip().lower()
            if key in COMPANY_ALIASES:
                result.add(COMPANY_ALIASES[key])
            elif key:
                result.add(item.strip())
        return result


def format_route(route: RouteOption, idx: int) -> str:
    lines = [
        f"{idx}) Путь: {' -> '.join(route.path)}",
        f"   Цена: {route.total_price} | Время в пути: {route.total_duration} мин | Пересадки: {route.transfers}",
    ]
    for seg in route.segments:
        dep = segment_departure_dt(seg)
        arr = segment_arrival_dt(seg)
        num = seg.flight_number or "—"
        lines.append(
            f"   - {seg.city_from} -> {seg.city_to} [{seg.transport}] рейс {num} | {seg.company}, {seg.price} руб, "
            f"{seg.duration_min} мин в пути | отправление {dep.strftime('%Y-%m-%d %H:%M')}, "
            f"прибытие {arr.strftime('%Y-%m-%d %H:%M')}"
        )
    return "\n".join(lines)


def route_option_to_dict(route: RouteOption) -> dict:
    return {
        "path": list(route.path),
        "total_price": route.total_price,
        "total_duration": route.total_duration,
        "transfers": route.transfers,
        "segments": [
            {
                "from": s.city_from,
                "to": s.city_to,
                "transport": s.transport,
                "company": s.company,
                "price": s.price,
                "duration_min": s.duration_min,
                "departure_date": s.departure_date,
                "departure_time": s.departure_time,
                "flight_number": s.flight_number,
            }
            for s in route.segments
        ],
    }


def route_dict_to_option(d: dict) -> RouteOption:
    segments: list[Segment] = []
    for s in d["segments"]:
        segments.append(
            Segment(
                city_from=s["from"],
                city_to=s["to"],
                transport=s["transport"],
                company=s["company"],
                price=int(s["price"]),
                duration_min=int(s["duration_min"]),
                departure_date=s["departure_date"],
                departure_time=s["departure_time"],
                flight_number=s.get("flight_number", ""),
            )
        )
    return RouteOption(
        path=list(d["path"]),
        segments=segments,
        total_price=int(d["total_price"]),
        total_duration=int(d["total_duration"]),
        transfers=int(d["transfers"]),
        preferred_hits=0,
    )


def print_cities_info(router: TravelRouter) -> None:
    print("\nДоступные города:")
    for name in sorted(router.cities):
        city = router.cities[name]
        services = []
        if city["has_bus_station"]:
            services.append("автовокзал")
        if city["has_train_station"]:
            services.append("жд")
        if city["has_airport"]:
            services.append("аэропорт")
        print(f"- {name}: {', '.join(services)}")


def run_route_search(router: TravelRouter, logged_in_user: str | None) -> None:
    print("\n--- Поиск маршрута ---")
    start_city = input("Начальный город: ").strip().upper()
    end_city = input("Город назначения: ").strip().upper()

    default_date = "2026-04-10"
    default_time = "00:00"
    date_input = input(f"Дата отправления не раньше (ГГГГ-ММ-ДД), Enter — {default_date}: ").strip()
    earliest_date = date_input or default_date
    time_input = input(f"Время не раньше (ЧЧ:ММ), Enter — {default_time}: ").strip()
    earliest_time = time_input or default_time

    direct_input = input("Только напрямую? (да/нет): ").strip().lower()
    direct_only = direct_input in {"да", "y", "yes", "1"}

    print("\nПриоритет:")
    print("1 - побыстрее")
    print("2 - подешевле")
    print("3 - оптимально")
    priority_input = input("Выбор (1/2/3): ").strip()
    priority = {"1": "fast", "2": "cheap", "3": "optimal"}.get(priority_input, "optimal")

    companies_raw = input(
        "Предпочитаемые компании через запятую (S7, Победа, Аэрофлот, РЖД) или all: "
    )
    preferred_companies = TravelRouter.normalize_companies(companies_raw)

    routes = router.find_routes(
        start=start_city,
        end=end_city,
        direct_only=direct_only,
        earliest_date=earliest_date,
        earliest_time=earliest_time,
        priority=priority,
        preferred_companies=preferred_companies,
    )

    print("\n=== Результаты (лучшие 5 вариантов) ===")
    if not routes:
        print("Нормальные варианты маршрута не найдены по выбранным параметрам.")
        return
    total_found = len(routes)
    top_routes = routes[:TOP_ROUTES_LIMIT]
    if total_found > TOP_ROUTES_LIMIT:
        print(f"Найдено вариантов: {total_found}. Показаны лучшие {TOP_ROUTES_LIMIT}.\n")
    for idx, route in enumerate(top_routes, start=1):
        print(format_route(route, idx))

    if logged_in_user:
        raw = input(
            "\nДобавить маршрут в избранное? Введите номер 1–"
            f"{len(top_routes)} или Enter чтобы пропустить: "
        ).strip()
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(top_routes):
                payload = route_option_to_dict(top_routes[n - 1])
                add_favorite_route(logged_in_user, payload)
                print("Маршрут сохранён в избранное.")
    else:
        print("\nЧтобы сохранять маршруты в избранное, войдите в аккаунт из главного меню.")


def show_favorites_screen(username: str) -> None:
    items = list_favorites(username)
    print("\n--- Избранное ---")
    if not items:
        print("Пока пусто. Найдите маршрут и добавьте его после поиска.")
        return
    for i, item in enumerate(items, start=1):
        print(f"\n{i}) Сохранено: {item.get('saved_at', '')} id={item.get('id', '')}")
        ro = route_dict_to_option(item["route"])
        print(format_route(ro, 1))
    del_raw = input("\nУдалить запись по номеру из списка (или Enter): ").strip()
    if del_raw.isdigit():
        n = int(del_raw)
        if 1 <= n <= len(items):
            remove_favorite(username, items[n - 1]["id"])
            print("Удалено.")


def auth_register_flow() -> None:
    u = input("Логин: ").strip()
    p = input("Пароль: ")
    ok, msg = register_user(u, p)
    print(msg if ok else msg)


def show_admin_accounts_screen() -> None:
    print("\n--- Учётные записи (только просмотр) ---")
    accounts = list_all_user_accounts()
    if not accounts:
        print("Нет пользователей.")
        return
    print(f"{'Логин':<20} {'Роль':<10}")
    print("-" * 32)
    for row in accounts:
        print(f"{row['username']:<20} {row['role']:<10}")


def auth_login_flow() -> str | None:
    u = input("Логин: ").strip()
    p = input("Пароль: ")
    if verify_login(u, p):
        name = canonical_username(u)
        print(f"Добро пожаловать, {name}!")
        return name
    print("Неверный логин или пароль.")
    return None


def run_console_app() -> None:
    router = TravelRouter(
        "data/cities/cities.json",
        "data/buses/by_operator",
        "data/trains/rzd.json",
        "data/planes",
    )
    current_user: str | None = None

    while True:
        print("\n=== Т-Путешествия (консольная версия) ===")
        print(f"Городов в базе: {router.total_cities}")
        if current_user:
            print(f"Вы вошли как: {current_user}")
        else:
            print("Вы не вошли в аккаунт.")
        print_cities_info(router)

        print("\nГлавное меню:")
        print("1 — Регистрация")
        print("2 — Вход")
        print("3 — Поиск маршрута")
        if current_user:
            print("4 — Моё избранное")
            print("5 — Выйти из аккаунта")
            if is_admin(current_user):
                print("6 — Админ: список учётных записей")
        print("0 — Выход из программы")

        choice = input("Выбор: ").strip()

        if choice == "0":
            print("До свидания.")
            break
        if choice == "1":
            auth_register_flow()
        elif choice == "2":
            current_user = auth_login_flow()
        elif choice == "3":
            run_route_search(router, current_user)
        elif choice == "4" and current_user:
            show_favorites_screen(current_user)
        elif choice == "5" and current_user:
            current_user = None
            print("Вы вышли из аккаунта.")
        elif choice == "6" and current_user and is_admin(current_user):
            show_admin_accounts_screen()
        else:
            print("Неверный пункт меню.")


if __name__ == "__main__":
    run_console_app()
