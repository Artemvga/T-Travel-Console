# Т-Путешествия

Веб-сервис для поиска маршрутов по городам России на основе билетов из локального датасета.

Проект вырос из консольной версии и сейчас состоит из:

- `backend/` — Django + Django REST Framework;
- `frontend/` — React + Vite;
- `data/` — города, перевозчики и билеты;
- `scripts/` — генерация и подготовка данных.

Сервис умеет:

- искать город по подсказкам;
- показывать карточку города с населением, регионом и транспортными хабами;
- строить маршрут между городами;
- учитывать приоритет пользователя: дешевле, быстрее или оптимально;
- фильтровать по видам транспорта и перевозчикам;
- учитывать обязательный транзитный город;
- показывать маршрут на карте и список подходящих билетов.

## Стек

- Backend: Python, Django, Django REST Framework, SQLite
- Frontend: React, Vite, Axios, React Router
- Данные: JSON / JSONL из `data/`
- Карта: Yandex Maps API

## Структура

```text
backend/
  apps/
    carriers/
    cities/
    routes/
    tickets/
  config/
  manage.py
  requirements.txt

frontend/
  src/
    components/
    pages/
    services/
    styles/
  public/
  package.json

data/
  cities/
  buses/
  trains/
  planes/
  commuter_trains/
  _tmp_ticket_jsonl/
```

## Что важно по данным

- Города берутся из `data/cities/cities.json`
- Автобусы — из `data/buses/by_operator/*.json`
- Поезда — из `data/trains/*.json`
- Самолеты — из `data/planes/*.json`
- При наличии временных генераторных файлов импорт билетов умеет читать `data/_tmp_ticket_jsonl/*.jsonl`

## Первый запуск

### 1. Backend

```bash
cd /Users/artem/Documents/T-Travel-Console/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_all
python manage.py runserver 127.0.0.1:8000
```

Если хотите быстрее поднять локальную БД для тестов, можно ограничить импорт:

```bash
python manage.py seed_all --max-tickets-per-file 5000
```

### 2. Frontend

```bash
cd /Users/artem/Documents/T-Travel-Console/frontend
npm install
npm run dev:frontend
```

По умолчанию frontend будет доступен на `http://127.0.0.1:5173`.

## Запуск backend и frontend вместе

После того как backend-виртуальное окружение создано и зависимости установлены:

```bash
cd /Users/artem/Documents/T-Travel-Console/frontend
npm install
npm run dev
```

Скрипт `npm run dev`:

- поднимает Django backend;
- если в SQLite ещё нет активных билетов, запускает импорт данных;
- запускает Vite frontend.

## Полезные backend-команды

```bash
cd /Users/artem/Documents/T-Travel-Console/backend
source .venv/bin/activate

python manage.py check
python manage.py test apps.routes
python manage.py import_cities
python manage.py import_carriers
python manage.py import_tickets --truncate
python manage.py cleanup_tickets
```

## Переменные окружения

Смотрите шаблон в `.env.example`.

Основные переменные:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_SQLITE_NAME`
- `DJANGO_TIME_ZONE`
- `VITE_API_BASE_URL`
- `VITE_YANDEX_MAPS_API_KEY`
- `T_TRAVEL_DATA_DIR`

Для карты маршрутов через Yandex Maps добавьте ключ во frontend-окружение:

```bash
cd /Users/artem/Documents/T-Travel-Console/frontend
printf 'VITE_YANDEX_MAPS_API_KEY=your_key_here\n' > .env.local
```

## API

Основные маршруты backend:

- `GET /api/health/`
- `GET /api/stats/`
- `GET /api/cities/`
- `GET /api/cities/search/?q=том`
- `GET /api/cities/<slug>/`
- `GET /api/carriers/`
- `POST /api/routes/build/`

Пример тела запроса на построение маршрута:

```json
{
  "from_city": "tomsk",
  "to_city": "moscow",
  "via_city": "novosibirsk",
  "departure_date": "2026-04-10",
  "departure_time": "08:00",
  "priority": "optimal",
  "preferred_carriers": ["s7", "rzd"],
  "preferred_transport_types": ["plane", "train"],
  "direct_only": false,
  "allow_transfers": true,
  "max_transfers": 2
}
```

## Текущее состояние

Сейчас проект находится на стадии функционального MVP:

- веб-каркас уже собран;
- backend работает с текущим датасетом проекта;
- поиск маршрутов оптимизирован относительно полного перебора в памяти;
- интерфейс пока выполнен в черно-белом каркасе, чтобы сначала закрыть функциональность.

Следующий естественный шаг для больших объёмов данных — переход с SQLite на PostgreSQL и дальнейшая оптимизация поиска под 10M+ билетов.
