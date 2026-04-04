import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def resolve_data_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path

    project_root = Path(settings.PROJECT_ROOT)
    data_dir = Path(settings.DATA_DIR)
    data_relative = Path(*path.parts[1:]) if path.parts and path.parts[0] == "data" else path
    candidates = [
        data_dir / data_relative,
        project_root / path,
        Path(settings.BASE_DIR) / path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def load_json(path_value: str):
    path = resolve_data_path(path_value)
    if not path.exists():
        raise CommandError(f"Data file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"Invalid JSON in {path}: {exc}") from exc


def parse_iso_datetime(value: str):
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid datetime value: {value}")
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed
