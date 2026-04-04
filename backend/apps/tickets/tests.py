import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cities.models import City
from apps.tickets.models import Ticket
from apps.tickets.providers import GeneratedTicketProvider
from apps.tickets.services.generation_service import GenerationConfig


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_test_dataset(data_dir: Path) -> None:
    write_json(
        data_dir / "cities" / "cities.json",
        {
            "meta": {"source": "tests"},
            "cities": [
                {
                    "name": "Новосибирск",
                    "region": "Новосибирская область",
                    "population": 1620000,
                    "lat": 55.031,
                    "lon": 82.928,
                    "has_airport": True,
                    "has_international_airport": True,
                    "has_train_station": True,
                    "has_bus_station": True,
                    "has_commuter_station": True,
                    "is_rail_hub": True,
                    "is_bus_hub": True,
                },
                {
                    "name": "Москва",
                    "region": "Москва",
                    "population": 13000000,
                    "lat": 55.755,
                    "lon": 37.617,
                    "has_airport": True,
                    "has_international_airport": True,
                    "has_train_station": True,
                    "has_bus_station": True,
                    "has_commuter_station": True,
                    "is_rail_hub": True,
                    "is_bus_hub": True,
                },
                {
                    "name": "Томск",
                    "region": "Томская область",
                    "population": 545000,
                    "lat": 56.501,
                    "lon": 84.992,
                    "has_airport": True,
                    "has_international_airport": False,
                    "has_train_station": True,
                    "has_bus_station": True,
                    "has_commuter_station": False,
                    "is_rail_hub": True,
                    "is_bus_hub": True,
                },
            ],
        },
    )
    write_json(
        data_dir / "trains" / "rzd.json",
        {
            "id": "rzd",
            "company": "РЖД",
            "category": "train",
            "tickets": [],
        },
    )
    write_json(
        data_dir / "commuter_trains" / "central_ppk.json",
        {
            "id": "central_ppk",
            "company": "ЦППК",
            "category": "electric_train",
            "tickets": [],
        },
    )
    write_json(
        data_dir / "buses" / "operators_index.json",
        {
            "operators": [
                {
                    "id": "novosibirsk-bus",
                    "company": "Новосибирский автовокзал",
                    "region": "Новосибирская область",
                    "city": "Новосибирск",
                    "tickets": [],
                }
            ]
        },
    )
    write_json(
        data_dir / "buses" / "by_operator" / "novosibirsk-bus.json",
        {
            "id": "novosibirsk-bus",
            "company": "Новосибирский автовокзал",
            "category": "bus",
            "tickets": [],
        },
    )
    (data_dir / "planes").mkdir(parents=True, exist_ok=True)
    (data_dir / "planes" / "aeroflot.json").write_text("", encoding="utf-8")
    (data_dir / "_tmp_ticket_jsonl").mkdir(parents=True, exist_ok=True)


class TicketDatasetMixin:
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        build_test_dataset(self.data_dir)
        self.settings_override = override_settings(DATA_DIR=self.data_dir)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.tmp.cleanup()
        super().tearDown()


class TicketGenerationTests(TicketDatasetMixin, TestCase):
    def test_generator_is_deterministic_for_same_seed(self):
        provider = GeneratedTicketProvider(data_dir=self.data_dir)
        config = GenerationConfig(
            total=20,
            start_date=datetime(2026, 4, 10),
            end_date=datetime(2026, 4, 10),
            seed=77,
            batch_id="deterministic-batch",
            tmp_dir=self.data_dir / "_tmp_ticket_jsonl",
            materialize_json=False,
            transport_types=("train",),
        )

        provider.generate(config)
        first_snapshot = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((self.data_dir / "_tmp_ticket_jsonl" / "generated" / "deterministic-batch").glob("*.jsonl"))
        }
        provider.generate(config)
        second_snapshot = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((self.data_dir / "_tmp_ticket_jsonl" / "generated" / "deterministic-batch").glob("*.jsonl"))
        }

        self.assertEqual(first_snapshot, second_snapshot)

    def test_import_is_idempotent_with_empty_plane_json_and_jsonl_fallback(self):
        jsonl_path = self.data_dir / "_tmp_ticket_jsonl" / "plane_aeroflot.jsonl"
        jsonl_path.write_text(
            json.dumps(
                {
                    "from_city": "Новосибирск",
                    "to_city": "Москва",
                    "company": "Аэрофлот",
                    "departure_date": "2026-04-10",
                    "departure_time": "09:00",
                    "price_rub": 8900,
                    "distance_km": 2800,
                    "duration_min": 250,
                    "mode": "plane",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        call_command("import_cities")
        call_command("import_carriers")
        call_command("import_tickets", jsonl_dir=str(self.data_dir / "_tmp_ticket_jsonl"))
        self.assertEqual(Ticket.objects.count(), 1)

        call_command("import_tickets", jsonl_dir=str(self.data_dir / "_tmp_ticket_jsonl"))
        self.assertEqual(Ticket.objects.count(), 1)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.carrier.code, "aeroflot")
        self.assertEqual(ticket.generation_batch, "legacy-dataset")


class TicketPipelineApiTests(TicketDatasetMixin, APITestCase):
    def test_generation_status_reports_dataset_state(self):
        response = self.client.get(reverse("ticket-generation-status"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["dataset_ready"])
        self.assertEqual(response.data["active_tickets_count"], 0)

    def test_reseed_tickets_builds_searchable_dataset(self):
        call_command(
            "reseed_tickets",
            total=24,
            seed=31,
            start_date="2026-04-10",
            end_date="2026-04-10",
            jsonl_dir=str(self.data_dir / "_tmp_ticket_jsonl"),
            transport_types=["train"],
        )

        status_response = self.client.get(reverse("ticket-generation-status"))
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["dataset_ready"])
        self.assertGreater(status_response.data["active_tickets_count"], 0)
        from_city = City.objects.get(name="Новосибирск")
        to_city = City.objects.get(name="Москва")

        route_response = self.client.post(
            reverse("route-build"),
            {
                "from_city": from_city.slug,
                "to_city": to_city.slug,
                "departure_date": "2026-04-10",
                "departure_time": "00:00",
                "priority": "optimal",
                "direct_only": False,
                "allow_transfers": True,
                "max_transfers": 2,
            },
            format="json",
        )
        self.assertEqual(route_response.status_code, 200)
        self.assertEqual(route_response.data["status"], "success")
        self.assertTrue(route_response.data["best_route"]["segments"])
