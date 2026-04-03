"""
Скелет клиента Яндекс.Геокодера (HTTP API 1.x).

Ключ задаётся через переменную окружения YANDEX_GEOCODE_API_KEY.
Локально можно: export YANDEX_GEOCODE_API_KEY='ваш-ключ'

Документация: https://yandex.ru/dev/maps/geocoder/
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

# Базовый URL (как в вашем примере; при необходимости замените на https)
GEOCODER_BASE_URL = "https://geocode-maps.yandex.ru/1.x/"


def get_api_key() -> str:
    return os.environ.get("YANDEX_GEOCODE_API_KEY", "").strip()


def geocode(query: str, api_key: str | None = None) -> dict:
    """
    Прямой запрос геокодирования: адрес или координаты в текстовом виде.
    Возвращает распарсенный JSON ответа или {"error": "..."} при ошибке.
    """
    key = api_key if api_key is not None else get_api_key()
    if not key:
        return {"error": "Не задан YANDEX_GEOCODE_API_KEY"}

    params = urllib.parse.urlencode(
        {
            "geocode": query,
            "apikey": key,
            "format": "json",
            "results": 1,
        }
    )
    url = f"{GEOCODER_BASE_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "T-Travel-Console/0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        return {"error": "HTTP", "code": e.code, "reason": str(e.reason)}
    except urllib.error.URLError as e:
        return {"error": "URL", "reason": str(e.reason)}
    except json.JSONDecodeError as e:
        return {"error": "JSON", "reason": str(e)}


def reverse_geocode(lon: float, lat: float, api_key: str | None = None) -> dict:
    """Обратное геокодирование: координаты в виде 'lon,lat'."""
    return geocode(f"{lon},{lat}", api_key=api_key)


if __name__ == "__main__":
    # Пример: python3 yandex_geocode.py
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "Москва, Красная площадь"
    print(json.dumps(geocode(q), ensure_ascii=False, indent=2))
