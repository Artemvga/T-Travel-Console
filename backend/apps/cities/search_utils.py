from collections import defaultdict


CITY_ALIASES = {
    "нск": "Новосибирск",
    "новосиб": "Новосибирск",
    "мск": "Москва",
    "спб": "Санкт-Петербург",
    "питер": "Санкт-Петербург",
    "екб": "Екатеринбург",
    "владик": "Владивосток",
}


ALIASES_BY_CITY = defaultdict(set)
for alias, city_name in CITY_ALIASES.items():
    ALIASES_BY_CITY[city_name.casefold()].add(alias)


def rank_city_match(city_name: str, query: str):
    normalized_name = city_name.casefold()
    best_rank = None

    if normalized_name == query:
        best_rank = 0
    elif normalized_name.startswith(query):
        best_rank = 1
    elif query in normalized_name:
        best_rank = 2

    for alias in ALIASES_BY_CITY.get(normalized_name, ()):
        if alias == query:
            best_rank = 0 if best_rank is None else min(best_rank, 0)
        elif alias.startswith(query):
            best_rank = 1 if best_rank is None else min(best_rank, 1)
        elif query in alias:
            best_rank = 2 if best_rank is None else min(best_rank, 2)

    return best_rank


def resolve_alias_name(query: str):
    return CITY_ALIASES.get(query.casefold())
