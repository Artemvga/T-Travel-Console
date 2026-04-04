from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.routes.models import RouteFavorite, RouteSearchLog
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Reset SQLite data, import catalog entities, regenerate tickets, import them, and rebuild snapshots."

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
        RouteFavorite.objects.all().delete()
        RouteSearchLog.objects.all().delete()
        Ticket.objects.all().delete()
        City.objects.all().delete()
        Carrier.objects.all().delete()

        call_command("import_cities")
        call_command("import_carriers")
        call_command(
            "regenerate_tickets",
            total=options["total"],
            seed=options["seed"],
            batch_id=options["batch_id"],
            start_date=options["start_date"],
            end_date=options["end_date"],
            jsonl_dir=options["jsonl_dir"],
            transport_types=options["transport_types"],
            materialize_json=options["materialize_json"],
            bus_weight=options["bus_weight"],
            train_weight=options["train_weight"],
            plane_weight=options["plane_weight"],
            electric_weight=options["electric_weight"],
        )
        call_command(
            "import_tickets",
            jsonl_dir=options["jsonl_dir"],
            batch_id=options["batch_id"],
            replace_batch=True,
        )
        call_command("refresh_catalog_snapshots")
        self.stdout.write(self.style.SUCCESS("Dataset reseeded successfully."))
