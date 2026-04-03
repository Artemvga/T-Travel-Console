from django.db.models import Case, CharField, Count, F, IntegerField, Q, When
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tickets.models import Ticket

from .models import City
from .search_utils import rank_city_match
from .serializers import CityDetailSerializer, CityListSerializer, CitySearchSerializer


class CityListAPIView(generics.ListAPIView):
    queryset = City.objects.order_by("name")
    serializer_class = CityListSerializer
    authentication_classes = []
    permission_classes = []


class CitySearchAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response([])

        normalized_query = query.casefold()
        matched_cities = []
        for city in City.objects.only(
            "id",
            "name",
            "slug",
            "region",
            "population",
            "latitude",
            "longitude",
        ).order_by("name"):
            rank = rank_city_match(city.name, normalized_query)
            if rank is None:
                continue
            matched_cities.append((rank, city.name, city))

        matched_cities.sort(key=lambda item: (item[0], item[1]))
        serializer = CitySearchSerializer(
            [item[2] for item in matched_cities[:10]],
            many=True,
        )
        return Response(serializer.data)


class CityDetailAPIView(generics.RetrieveAPIView):
    queryset = City.objects.all()
    serializer_class = CityDetailSerializer
    lookup_field = "slug"
    authentication_classes = []
    permission_classes = []

    def get_object(self):
        city = super().get_object()
        active_tickets = Ticket.objects.filter(
            Q(from_city=city) | Q(to_city=city),
            is_active=True,
        )

        related_destinations = active_tickets.annotate(
            related_city_id=Case(
                When(from_city=city, then=F("to_city_id")),
                default=F("from_city_id"),
                output_field=IntegerField(),
            ),
            related_city_name=Case(
                When(from_city=city, then=F("to_city__name")),
                default=F("from_city__name"),
                output_field=CharField(),
            ),
            related_city_slug=Case(
                When(from_city=city, then=F("to_city__slug")),
                default=F("from_city__slug"),
                output_field=CharField(),
            ),
        )

        popular_destinations_rows = (
            related_destinations
            .values("related_city_id", "related_city_name", "related_city_slug")
            .annotate(total=Count("id"))
            .order_by("-total", "related_city_name")[:4]
        )

        transport_rows = (
            active_tickets.values("transport_type")
            .annotate(total=Count("id"))
            .order_by("transport_type")
        )

        popular_destinations = [
            {
                "name": row["related_city_name"],
                "slug": row["related_city_slug"],
                "tickets_count": row["total"],
            }
            for row in popular_destinations_rows
        ]

        city.available_directions_count = (
            related_destinations.values("related_city_id").distinct().count()
        )
        city.active_tickets_count = active_tickets.count()
        city.tickets_by_transport = [
            {
                "transport_type": row["transport_type"],
                "tickets_count": row["total"],
            }
            for row in transport_rows
        ]
        city.popular_destinations = popular_destinations
        city.city_energy = active_tickets.values("carrier_id").distinct().count()
        return city
