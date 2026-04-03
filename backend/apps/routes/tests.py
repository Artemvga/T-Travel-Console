from datetime import datetime, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.carriers.models import Carrier
from apps.cities.models import City
from apps.tickets.models import Ticket


def aware(value: str):
    return timezone.make_aware(
        datetime.strptime(value, "%Y-%m-%d %H:%M"),
        timezone.get_current_timezone(),
    )


class TravelAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tomsk = City.objects.create(
            name="Томск",
            slug="tomsk",
            region="Томская область",
            population=545000,
            latitude=56.501,
            longitude=84.992,
            has_airport=True,
            has_train_station=True,
            has_bus_station=True,
            has_commuter_station=False,
        )
        cls.novosibirsk = City.objects.create(
            name="Новосибирск",
            slug="novosibirsk",
            region="Новосибирская область",
            population=1620000,
            latitude=55.031,
            longitude=82.928,
            has_airport=True,
            has_train_station=True,
            has_bus_station=True,
            has_commuter_station=True,
        )
        cls.moscow = City.objects.create(
            name="Москва",
            slug="moscow",
            region="Москва",
            population=13000000,
            latitude=55.755,
            longitude=37.617,
            has_airport=True,
            has_train_station=True,
            has_bus_station=True,
            has_commuter_station=True,
        )
        cls.omsk = City.objects.create(
            name="Омск",
            slug="omsk",
            region="Омская область",
            population=1110000,
            latitude=54.989,
            longitude=73.369,
            has_airport=True,
            has_train_station=True,
            has_bus_station=True,
            has_commuter_station=False,
        )

        cls.s7 = Carrier.objects.create(
            code="s7",
            name="S7",
            transport_type=Carrier.TransportType.PLANE,
            reference_url="https://www.s7.ru/",
        )
        cls.rzd = Carrier.objects.create(
            code="rzd",
            name="РЖД",
            transport_type=Carrier.TransportType.TRAIN,
            reference_url="https://www.rzd.ru/",
        )
        cls.bus = Carrier.objects.create(
            code="nsk-bus",
            name="Новосибирский автовокзал",
            transport_type=Carrier.TransportType.BUS,
        )

        cls._create_ticket(
            "bus-1",
            cls.bus,
            cls.tomsk,
            cls.novosibirsk,
            Ticket.TransportType.BUS,
            aware("2026-04-10 08:00"),
            240,
            1200,
            260,
        )
        cls._create_ticket(
            "plane-1",
            cls.s7,
            cls.novosibirsk,
            cls.moscow,
            Ticket.TransportType.PLANE,
            aware("2026-04-10 14:00"),
            250,
            9000,
            2800,
        )
        cls._create_ticket(
            "train-1",
            cls.rzd,
            cls.tomsk,
            cls.moscow,
            Ticket.TransportType.TRAIN,
            aware("2026-04-10 09:00"),
            1800,
            4500,
            3600,
        )
        cls._create_ticket(
            "plane-2",
            cls.s7,
            cls.tomsk,
            cls.moscow,
            Ticket.TransportType.PLANE,
            aware("2026-04-10 11:00"),
            240,
            12000,
            2900,
        )

    @classmethod
    def _create_ticket(
        cls,
        external_id,
        carrier,
        from_city,
        to_city,
        transport_type,
        departure_at,
        duration_minutes,
        price,
        distance_km,
    ):
        Ticket.objects.create(
            external_id=external_id,
            carrier=carrier,
            from_city=from_city,
            to_city=to_city,
            transport_type=transport_type,
            departure_datetime=departure_at,
            arrival_datetime=departure_at + timedelta(minutes=duration_minutes),
            duration_minutes=duration_minutes,
            price=price,
            distance_km=distance_km,
            is_direct=True,
            available_seats=20,
            is_active=True,
            last_synced_at=timezone.now(),
        )

    def test_city_search_returns_results(self):
        response = self.client.get(reverse("city-search"), {"q": "новос"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["slug"] == "novosibirsk" for item in response.data))

    def test_stats_exposes_transport_sections(self):
        response = self.client.get(reverse("dataset-stats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("transport_sections", response.data)
        self.assertTrue(any(section["tickets_count"] for section in response.data["transport_sections"]))

    def test_city_detail_contains_city_profile(self):
        response = self.client.get(reverse("city-detail", kwargs={"slug": self.tomsk.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["region"], "Томская область")
        self.assertEqual(response.data["population"], 545000)
        self.assertIn("train", response.data["available_transports"])
        self.assertIn("bus", response.data["available_transports"])

    def test_route_builder_returns_best_route(self):
        response = self.client.post(
            reverse("route-build"),
            {
                "from_city": self.tomsk.slug,
                "to_city": self.moscow.slug,
                "departure_date": "2026-04-10",
                "departure_time": "07:00",
                "priority": "fastest",
                "direct_only": False,
                "allow_transfers": True,
                "max_transfers": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIsNotNone(response.data["best_route"])
        self.assertEqual(response.data["best_route"]["segments"][0]["transport_type"], "plane")

    def test_route_builder_supports_required_transit_city(self):
        response = self.client.post(
            reverse("route-build"),
            {
                "from_city": self.tomsk.slug,
                "to_city": self.moscow.slug,
                "via_city": self.novosibirsk.slug,
                "departure_date": "2026-04-10",
                "departure_time": "07:00",
                "priority": "optimal",
                "direct_only": False,
                "allow_transfers": True,
                "max_transfers": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["query"]["via_city_slug"], self.novosibirsk.slug)
        waypoint_slugs = [
            waypoint["slug"] for waypoint in response.data["best_route"]["waypoints"]
        ]
        self.assertIn(self.novosibirsk.slug, waypoint_slugs[1:-1])

    def test_route_builder_validates_equal_cities(self):
        response = self.client.post(
            reverse("route-build"),
            {
                "from_city": self.tomsk.slug,
                "to_city": self.tomsk.slug,
                "departure_date": "2026-04-10",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
