from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.routes.models import RouteSearchLog
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Reset tables and import the current project dataset into SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-tickets-per-file",
            type=int,
            default=None,
            help="Optional cap per source file for faster local bootstrap.",
        )

    def handle(self, *args, **options):
        RouteSearchLog.objects.all().delete()
        Ticket.objects.all().delete()
        City.objects.all().delete()
        Carrier.objects.all().delete()
        call_command("import_cities")
        call_command("import_carriers")
        import_kwargs = {"truncate": True}
        if options.get("max_tickets_per_file") is not None:
            import_kwargs["max_tickets_per_file"] = options["max_tickets_per_file"]
        call_command("import_tickets", **import_kwargs)
        self.stdout.write(self.style.SUCCESS("Current dataset imported successfully."))
