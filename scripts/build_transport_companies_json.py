#!/usr/bin/env python3
"""Генерирует JSON по перевозчикам из списка (автобусы — по одному файлу + сводный)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# (id_slug, регион, город/примечание, название оператора, url)
BUS_ROWS: list[tuple[str, str, str, str, str]] = [
    ("amur_amurasso", "Амурская область", "Благовещенск", "Международный автовокзал «Амурассо»", "https://www.avtovokzaly.ru/raspisanie/blagoveshensk/mezhdunarodnyj_avtovokzal_amurasso"),
    ("arkhangelsk", "Архангельская область", "Архангельск", "Автовокзал Архангельска", "https://www.avtovokzaly.ru/raspisanie/arhangelsk/avtovokzal"),
    ("astrakhan", "Астраханская область", "Астрахань", "Автовокзал Астрахани", "https://av30.ru/"),
    ("belgorod_etk", "Белгородская область", "пгт Северный (Белгородский район)", "ЕТК", "https://etk31.ru/"),
    ("bryansk", "Брянская область", "Брянск", "Автостанция города Брянска", "https://avtovokzal-br.ru/"),
    ("vladimir", "Владимирская область", "Владимир", "Объединение автовокзалов и автостанций Владимирской области", "https://vladavtovokzal.ru/"),
    ("volgograd", "Волгоградская область", "Волгоград", "Автовокзал Волгоград", "https://avtovokzal-volgograd.ru/"),
    ("vologda", "Вологодская область", "Вологда", "Вологодский автовокзал", "https://avtovokzal35.ru/"),
    ("voronezh", "Воронежская область", "Воронеж", "Центральный автовокзал Воронежа", "https://vokzal36.ru/"),
    ("ivanovo", "Ивановская область", "Иваново", "Ивановское объединение автовокзалов", "https://av37.ru/ivanovo/"),
    ("irkutsk", "Иркутская область", "Иркутск", "Автовокзал-Онлайн", "https://avtovokzal-on-line.ru/"),
    ("kaliningrad", "Калининградская область", "Калининград", "АО «Автовокзал»", "https://avl39.ru/"),
    ("kaluga", "Калужская область", "Калуга", "Автовокзал Калуги", "https://av-kaluga.ru/"),
    ("kemerovo", "Кемеровская область", "Кемерово", "Автовокзал Кемерово / Автовокзалы Кузбасса", "https://xn--80abcuo9bal.xn--p1ai/"),
    ("kirov", "Кировская область", "Киров", "Автовокзал Кирова", "https://kirovkpat.ru/"),
    ("kostroma", "Костромская область", "Кострома", "Автовокзал Костромы", "https://av-kostroma.ru/"),
    ("kurgan", "Курганская область", "Курган", "Курганский автовокзал", "https://av45.ru/"),
    ("kursk", "Курская область", "Курск", "Курский автовокзал", "https://autovokzal46.ru/"),
    ("lenobl", "Ленинградская область", "Санкт-Петербург", "ГКУ ЛО «Леноблтранс»", "https://gkulot.ru/"),
    ("lipetsk", "Липецкая область", "Липецк", "Автовокзал Липецк", "https://avtovokzal48.ru/"),
    ("magadan", "Магаданская область", "Магадан", "Автовокзал Магадана", "https://www.avtovokzaly.ru/raspisanie/magadan/avtovokzal"),
    ("mostransavto", "Московская область", "Московская область", "Мострансавто", "https://mostransavto.ru/?page=about"),
    ("murmansk", "Мурманская область", "Мурманск", "АО «Мурманскавтотранс»", "https://murmanskavtotrans.ru/"),
    ("nizhny_novgorod", "Нижегородская область", "Нижний Новгород", "Нижегородпассажиравтотранс", "https://npat.ru/"),
    ("veliky_novgorod", "Новгородская область", "Великий Новгород", "АО «Автобусный парк»", "https://buspark53.ru/"),
    ("novosibirsk", "Новосибирская область", "Новосибирск", "Новосибирский автовокзал-Главный", "https://nskavtovokzal.ru/"),
    ("omsk", "Омская область", "Омск", "Омскоблавтотранс", "https://omskoblauto.ru/"),
    ("orenburg", "Оренбургская область", "Оренбург", "Автовокзал Оренбург", "https://av56.ru/"),
    ("orel", "Орловская область", "Орёл", "Орёлавтотранс / автовокзалы Орловской области", "https://xn--57-6kcaja9axlzb9b.xn--p1ai/"),
    ("penza", "Пензенская область", "Пенза", "Автовокзал Пенза", "https://avtovokzal-penza.ru/penza/"),
    ("pskov", "Псковская область", "Псков", "АО «Псковпассажиравтотранс»", "https://www.pskovbus.ru/"),
    ("rostov", "Ростовская область", "Ростов-на-Дону", "Областной автовокзал «Центральный»", "https://centrobus.ru/"),
    ("ryazan", "Рязанская область", "Рязань", "Автовокзалы Рязани и области", "https://autovokzal62.ru/"),
    ("samara", "Самарская область", "Самара", "Автовокзал Самары", "https://avokzal63.ru/"),
    ("saratov", "Саратовская область", "Саратов", "Автовокзал Саратова", "https://avv64.ru/"),
    ("sakhalin", "Сахалинская область", "Южно-Сахалинск", "АО «Транспортная компания»", "https://65bus.ru/"),
    ("ekaterinburg", "Свердловская область", "Екатеринбург", "Свердловское областное объединение пассажирского автотранспорта (автовокзал «Южный»)", "https://autovokzal.org/"),
    ("smolensk", "Смоленская область", "Смоленск", "Автовокзал Смоленска", "https://smolavtovokzal.ru/"),
    ("tambov", "Тамбовская область", "Тамбов", "Автовокзал Тамбов", "https://tambov-avtovokzal.ru/"),
    ("tver", "Тверская область", "Тверь", "Тверьавтотранс", "https://www.tverautotrans.ru/"),
    ("tomsk", "Томская область", "Томск", "АО «Томскавтотранс»", "https://tomskavtotrans.ru/"),
    ("tula", "Тульская область", "Тула", "ООО «ТУЛААВТОТРАНС»", "https://tula-avtotrans.ru/"),
    ("tyumen", "Тюменская область", "Тюмень", "ГБУ ТО «Объединение АВ и АС»", "https://vokzal72.ru/tyumen/"),
    ("ulyanovsk", "Ульяновская область", "Ульяновск", "АО «ПАТП-1»", "https://auto.patp-ul.ru/"),
    ("chelyabinsk", "Челябинская область", "Челябинск", "Центральный автовокзал «Синегорье»", "https://www.avtovokzaly.ru/raspisanie/chelyabinsk/avtovokzal_sinegore"),
    ("yaroslavl", "Ярославская область", "Ярославль", "Яавтобус", "https://www.t-ya.ru/"),
]


def strip_tracking(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, "", ""))


def bus_operator_doc(slug: str, region: str, city: str, company: str, url: str) -> dict:
    return {
        "schema_version": 1,
        "category": "bus",
        "id": slug,
        "region": region,
        "city": city,
        "company": company,
        "reference_url": strip_tracking(url),
        "tickets": [],
    }


def main() -> None:
    buses_dir = DATA / "buses" / "by_operator"
    buses_dir.mkdir(parents=True, exist_ok=True)

    operators: list[dict] = []
    for slug, region, city, company, url in BUS_ROWS:
        doc = bus_operator_doc(slug, region, city, company, url)
        operators.append(doc)
        out = buses_dir / f"{slug}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    index = {
        "meta": {
            "category": "bus",
            "description": "Автобусные перевозки по регионам (операторы / автовокзалы)",
            "count": len(operators),
        },
        "operators": operators,
    }
    with open(DATA / "buses" / "operators_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # Удаляем устаревшие заглушки, если есть
    for old in ("avtovokzal.json", "intercity_bus.json"):
        p = DATA / "buses" / old
        if p.exists():
            p.unlink()

    print(f"OK: {len(operators)} bus JSON in {buses_dir}, index: buses/operators_index.json")

    planes_dir = DATA / "planes"
    planes_dir.mkdir(parents=True, exist_ok=True)
    planes = [
        ("aeroflot", "Аэрофлот", "https://www.aeroflot.ru/"),
        ("s7", "S7 Airlines", "https://www.s7.ru/"),
        ("pobeda", "Победа", "https://www.flypobeda.ru/"),
    ]
    for slug, name, url in planes:
        doc = {
            "schema_version": 1,
            "category": "plane",
            "id": slug,
            "company": name,
            "reference_url": strip_tracking(url),
            "tickets": [],
        }
        with open(planes_dir / f"{slug}.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    trains_dir = DATA / "trains"
    trains_dir.mkdir(parents=True, exist_ok=True)
    rzd_doc = {
        "schema_version": 1,
        "category": "train",
        "id": "rzd",
        "company": "РЖД",
        "reference_url": "https://www.rzd.ru/",
        "tickets": [],
    }
    with open(trains_dir / "rzd.json", "w", encoding="utf-8") as f:
        json.dump(rzd_doc, f, ensure_ascii=False, indent=2)

    index_air_rail = {
        "meta": {"description": "Авиа и ж/д"},
        "planes": [p[1] for p in planes],
        "trains": ["РЖД"],
    }
    with open(DATA / "planes_trains_index.json", "w", encoding="utf-8") as f:
        json.dump(index_air_rail, f, ensure_ascii=False, indent=2)

    print("OK: planes/*.json, trains/rzd.json, planes_trains_index.json")


if __name__ == "__main__":
    main()
