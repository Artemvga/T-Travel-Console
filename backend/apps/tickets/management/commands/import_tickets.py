from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.tickets.services.import_service import TicketImportService


class Command(BaseCommand):
    help = "Import tickets from generated batch JSONL or legacy project dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jsonl-dir",
            default="data/_tmp_ticket_jsonl",
            help="Directory with generated batch JSONL and legacy fallback files.",
        )
        parser.add_argument(
            "--batch-id",
            default=None,
            help="Optional generated batch id. If omitted, the latest generated batch is used.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete all existing tickets before import.",
        )
        parser.add_argument(
            "--replace-batch",
            action="store_true",
            help="Delete current tickets for the imported generation batch before import.",
        )
        parser.add_argument(
            "--max-tickets-per-file",
            type=int,
            default=None,
            help="Optional cap per source file for faster local seeding.",
        )

    def handle(self, *args, **options):
        if not City.objects.exists():
            call_command("import_cities")
        if not Carrier.objects.exists():
            call_command("import_carriers")

        service = TicketImportService(jsonl_dir=options["jsonl_dir"])
        stats = service.import_tickets(
            truncate=options["truncate"],
            batch_id=options.get("batch_id"),
            replace_batch=options["replace_batch"],
            max_tickets_per_file=options.get("max_tickets_per_file"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Tickets import completed: "
                f"{stats.created} created, {stats.skipped} skipped, "
                f"source={stats.source_kind}, batch={stats.generation_batch or 'n/a'}."
            )
        )
