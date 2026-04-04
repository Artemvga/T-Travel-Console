from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compatibility wrapper for reseed_tickets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-tickets-per-file",
            type=int,
            default=None,
            help="Optional cap per source file for faster local bootstrap.",
        )

    def handle(self, *args, **options):
        total = 100_000
        if options.get("max_tickets_per_file") is not None:
            # Preserve the old lightweight bootstrap intent by roughly scaling down generation.
            total = max(500, options["max_tickets_per_file"] * 8)
        call_command("reseed_tickets", total=total)
        self.stdout.write(self.style.SUCCESS("Current dataset imported successfully."))
