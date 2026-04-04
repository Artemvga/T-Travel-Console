import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.tickets.models import Ticket

from .models import RouteFavorite, RouteSearchLog
from .serializers import (
    RouteBuildRequestSerializer,
    RouteFavoriteSerializer,
    RouteFavoriteWriteSerializer,
)
from .services import build_routes, resolve_city


TRANSPORT_LABELS = {
    "plane": "Самолеты",
    "train": "Поезда",
    "bus": "Автобусы",
    "electric_train": "Электрички",
}


def _snapshot_dir() -> Path:
    return Path(settings.DATA_DIR) / "cache"


def _read_snapshot(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _build_route_signature(route_data):
    segments = route_data.get("segments") or []
    signature = "|".join(
        segment.get("external_id", "")
        for segment in segments
        if segment.get("external_id")
    )
    if not signature:
        raise ValueError("Невозможно сохранить маршрут без сегментов.")
    return signature[:1024]


def _parse_departure_at(query):
    departure_date = query.get("departure_date", "")
    departure_time = query.get("departure_time", "")
    parsed_datetime = datetime.fromisoformat(f"{departure_date}T{departure_time}")
    if timezone.is_naive(parsed_datetime):
        return timezone.make_aware(parsed_datetime)
    return parsed_datetime


def _default_route_title(route_data, fallback_title="Маршрут"):
    waypoints = route_data.get("waypoints") or []
    if len(waypoints) >= 2:
        return f"{waypoints[0]['name']} → {waypoints[-1]['name']}"
    return fallback_title


class RouteBuildAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RouteBuildRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            from_city = resolve_city(payload["from_city"])
            to_city = resolve_city(payload["to_city"])
            via_city = (
                resolve_city(payload["via_city"]) if payload.get("via_city") else None
            )
            result = build_routes(payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        RouteSearchLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            from_city=from_city,
            via_city=via_city,
            to_city=to_city,
            departure_at=timezone.make_aware(
                datetime.combine(payload["departure_date"], payload["departure_time"])
            ),
            priority_mode=payload["priority"],
            selected_transport=payload.get("preferred_transport_types") or [],
            selected_carriers=payload.get("preferred_carriers") or [],
        )

        return Response(result)


class HealthCheckAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class DatasetStatsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        snapshot = _read_snapshot(_snapshot_dir() / "stats_snapshot.json")
        if snapshot is not None:
            return Response(snapshot)

        active_tickets = Ticket.objects.filter(is_active=True)

        transport_rows = (
            active_tickets.values("transport_type")
            .annotate(total=Count("id"))
            .order_by("transport_type")
        )
        transport_counts = {
            row["transport_type"]: row["total"] for row in transport_rows
        }

        carrier_rows = (
            active_tickets.values("transport_type", "carrier__name")
            .annotate(total=Count("id"))
            .order_by("transport_type", "-total", "carrier__name")
        )
        carriers_by_transport: dict[str, list[dict]] = defaultdict(list)
        for row in carrier_rows:
            carriers_by_transport[row["transport_type"]].append(
                {
                    "name": row["carrier__name"],
                    "tickets_count": row["total"],
                }
            )

        popular_direction_rows = (
            active_tickets.values(
                "transport_type",
                "from_city__name",
                "to_city__name",
            )
            .annotate(total=Count("id"))
            .order_by("transport_type", "-total", "from_city__name", "to_city__name")
        )
        popular_directions_by_transport: dict[str, list[dict]] = defaultdict(list)
        for row in popular_direction_rows:
            transport_type = row["transport_type"]
            if len(popular_directions_by_transport[transport_type]) >= 5:
                continue
            popular_directions_by_transport[transport_type].append(
                {
                    "from_city": row["from_city__name"],
                    "to_city": row["to_city__name"],
                    "tickets_count": row["total"],
                }
            )

        transport_sections = []
        for transport_type, label in TRANSPORT_LABELS.items():
            transport_sections.append(
                {
                    "transport_type": transport_type,
                    "label": label,
                    "tickets_count": transport_counts.get(transport_type, 0),
                    "carriers": carriers_by_transport.get(transport_type, []),
                    "popular_directions": popular_directions_by_transport.get(
                        transport_type, []
                    ),
                }
            )

        return Response(
            {
                "cities_count": City.objects.count(),
                "carriers_count": Carrier.objects.filter(is_active=True).count(),
                "tickets_count": Ticket.objects.count(),
                "active_tickets_count": active_tickets.count(),
                "searches_count": RouteSearchLog.objects.count(),
                "tickets_by_transport": transport_counts,
                "transport_sections": transport_sections,
            }
        )


class FavoriteRouteListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = (
            RouteFavorite.objects.filter(user=request.user)
            .select_related("from_city", "via_city", "to_city")
            .order_by("-created_at")
        )
        return Response(RouteFavoriteSerializer(favorites, many=True).data)

    def post(self, request):
        serializer = RouteFavoriteWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        query = payload["query"]
        route_data = payload["route_data"]

        try:
            departure_at = _parse_departure_at(query)
            route_signature = _build_route_signature(route_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        favorite, created = RouteFavorite.objects.update_or_create(
            user=request.user,
            route_signature=route_signature,
            departure_at=departure_at,
            defaults={
                "from_city": City.objects.filter(slug=query.get("from_city_slug")).first(),
                "via_city": City.objects.filter(slug=query.get("via_city_slug")).first(),
                "to_city": City.objects.filter(slug=query.get("to_city_slug")).first(),
                "priority_mode": query.get("priority", "optimal"),
                "route_title": payload.get("route_title")
                or _default_route_title(route_data),
                "route_data": route_data,
            },
        )

        response_serializer = RouteFavoriteSerializer(favorite)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FavoriteRouteDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted_count, _ = RouteFavorite.objects.filter(
            user=request.user,
            pk=pk,
        ).delete()
        if not deleted_count:
            return Response(
                {"detail": "Маршрут в избранном не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
