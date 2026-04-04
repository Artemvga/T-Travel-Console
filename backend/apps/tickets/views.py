from django.db.models import Count, Max, Min
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tickets.models import Ticket


class TicketGenerationStatusAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        active_tickets = Ticket.objects.filter(is_active=True)
        summary = active_tickets.aggregate(
            active_tickets_count=Count("id"),
            min_departure_date=Min("departure_datetime"),
            max_departure_date=Max("departure_datetime"),
            last_generation_at=Max("last_synced_at"),
        )
        latest_batch = (
            Ticket.objects.exclude(generation_batch="")
            .values("generation_batch")
            .annotate(last_generation_at=Max("last_synced_at"))
            .order_by("-last_generation_at", "-generation_batch")
            .first()
        )

        return Response(
            {
                "dataset_ready": bool(summary["active_tickets_count"]),
                "active_generation_batch": latest_batch["generation_batch"] if latest_batch else None,
                "active_tickets_count": summary["active_tickets_count"] or 0,
                "min_departure_date": summary["min_departure_date"].date().isoformat()
                if summary["min_departure_date"]
                else None,
                "max_departure_date": summary["max_departure_date"].date().isoformat()
                if summary["max_departure_date"]
                else None,
                "last_generation_at": summary["last_generation_at"].isoformat()
                if summary["last_generation_at"]
                else None,
            }
        )
