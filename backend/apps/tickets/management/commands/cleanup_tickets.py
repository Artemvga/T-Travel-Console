from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Deactivate departed or stale tickets and remove very old inactive records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stale-hours",
            type=int,
            default=48,
            help="Deactivate tickets not synced for more than N hours.",
        )
        parser.add_argument(
            "--delete-after-days",
            type=int,
            default=30,
            help="Delete inactive tickets older than N days after departure.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        stale_before = now - timedelta(hours=options["stale_hours"])
        delete_before = now - timedelta(days=options["delete_after_days"])

        departed = Ticket.objects.filter(
            departure_datetime__lt=now,
            is_active=True,
        ).update(is_active=False)

        stale = Ticket.objects.filter(
            last_synced_at__lt=stale_before,
            is_active=True,
        ).update(is_active=False)

        deleted, _ = Ticket.objects.filter(
            is_active=False,
            departure_datetime__lt=delete_before,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup completed: {departed} departed deactivated, "
                f"{stale} stale deactivated, {deleted} deleted."
            )
        )
