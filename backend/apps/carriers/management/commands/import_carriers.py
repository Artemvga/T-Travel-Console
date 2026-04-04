from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.carriers.models import Carrier
from apps.common.io import load_json, resolve_data_path


TRANSPORT_DIRS = {
    "plane": "data/planes",
    "train": "data/trains",
    "bus": "data/buses/by_operator",
    "electric_train": "data/commuter_trains",
}

FALLBACK_CARRIER_NAMES = {
    "aeroflot": "Аэрофлот",
    "s7": "S7 Airlines",
    "pobeda": "Победа",
    "rzd": "РЖД",
    "rzd_prigorod": "РЖД Пригород",
    "central_ppk": "ЦППК",
}


def _fallback_payload(file_path, transport_type: str) -> dict:
    code = file_path.stem
    return {
        "id": code,
        "company": FALLBACK_CARRIER_NAMES.get(
            code,
            code.replace("_", " ").replace("-", " ").title(),
        ),
        "reference_url": "",
        "category": transport_type,
        "source_recovery": "filename_fallback",
    }


class Command(BaseCommand):
    help = "Import carriers by scanning current dataset files."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        with transaction.atomic():
            for transport_type, relative_path in TRANSPORT_DIRS.items():
                directory = resolve_data_path(relative_path)
                if not directory.exists():
                    continue

                for file_path in sorted(directory.glob("*.json")):
                    try:
                        payload = load_json(str(file_path))
                    except CommandError:
                        payload = _fallback_payload(file_path, transport_type)
                    code = payload.get("id") or file_path.stem
                    carrier, is_created = Carrier.objects.update_or_create(
                        code=code,
                        defaults={
                            "name": payload.get("company") or payload.get("name") or code,
                            "transport_type": transport_type,
                            "reference_url": payload.get("reference_url", ""),
                            "metadata": {
                                key: value
                                for key, value in payload.items()
                                if key not in {"tickets"}
                            },
                            "is_active": True,
                        },
                    )
                    created += int(is_created)
                    updated += int(not is_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Carriers import completed: {created} created, {updated} updated."
            )
        )
