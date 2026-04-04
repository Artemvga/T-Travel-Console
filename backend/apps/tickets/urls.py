from django.urls import path

from .views import TicketGenerationStatusAPIView

urlpatterns = [
    path(
        "tickets/generation-status/",
        TicketGenerationStatusAPIView.as_view(),
        name="ticket-generation-status",
    ),
]
