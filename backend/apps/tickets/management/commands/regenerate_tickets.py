from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tickets.providers import GeneratedTicketProvider
from apps.tickets.services.generation_service import GenerationConfig


class Command(BaseCommand):
    help = "Generate a deterministic ticket batch into data/_tmp_ticket_jsonl/generated/<batch-id>/."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100_000)
        parser.add_argument("--seed", type=int, default=20260404)
        parser.add_argument("--batch-id", type=str, default=None)
        parser.add_argument("--start-date", type=str, default="2026-04-10")
        parser.add_argument("--end-date", type=str, default="2026-12-31")
        parser.add_argument(
            "--jsonl-dir",
            type=str,
            default="data/_tmp_ticket_jsonl",
        )
        parser.add_argument(
            "--transport-types",
            nargs="*",
            default=(),
            help="Optional subset: plane train bus electric_train",
        )
        parser.add_argument(
            "--materialize-json",
            action="store_true",
            help="Also export compatibility JSON files per carrier.",
        )
        parser.add_argument("--bus-weight", type=int, default=40)
        parser.add_argument("--train-weight", type=int, default=30)
        parser.add_argument("--plane-weight", type=int, default=20)
        parser.add_argument("--electric-weight", type=int, default=10)

    def handle(self, *args, **options):
        start_date = datetime.strptime(options["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(options["end_date"], "%Y-%m-%d")
        batch_id = options["batch_id"] or self._default_batch_id(
            start_date=options["start_date"],
            end_date=options["end_date"],
            seed=options["seed"],
            total=options["total"],
        )
        jsonl_dir = self._resolve_jsonl_dir(options["jsonl_dir"])
        provider = GeneratedTicketProvider(data_dir=settings.DATA_DIR)
        result = provider.generate(
            GenerationConfig(
                total=options["total"],
                start_date=start_date,
                end_date=end_date,
                seed=options["seed"],
                batch_id=batch_id,
                tmp_dir=jsonl_dir,
                materialize_json=options["materialize_json"],
                transport_types=tuple(options["transport_types"] or ()),
                weights={
                    "plane": options["plane_weight"],
                    "train": options["train_weight"],
                    "bus": options["bus_weight"],
                    "electric_train": options["electric_weight"],
                },
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {result.total_generated} tickets into {result.batch_dir} "
                f"(batch={result.batch_id})."
            )
        )

    def _default_batch_id(self, *, start_date: str, end_date: str, seed: int, total: int) -> str:
        return f"seed-{seed}-{start_date}-{end_date}-{total}"

    def _resolve_jsonl_dir(self, value: str) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        if value.startswith("data/"):
            return Path(settings.DATA_DIR) / Path(*path.parts[1:])
        return settings.DATA_DIR / value
