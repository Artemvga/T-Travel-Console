#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from apps.tickets.providers import GeneratedTicketProvider
from apps.tickets.services.generation_service import GenerationConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic ticket batches from local city and carrier data."
    )
    parser.add_argument("--total", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260404)
    parser.add_argument("--batch-id", type=str, default=None)
    parser.add_argument("--start-date", type=str, default="2026-04-10")
    parser.add_argument("--end-date", type=str, default="2026-12-31")
    parser.add_argument("--tmp-dir", type=str, default="data/_tmp_ticket_jsonl")
    parser.add_argument(
        "--transport-types",
        nargs="*",
        default=(),
        help="Optional subset: plane train bus electric_train",
    )
    parser.add_argument("--bus-weight", type=int, default=40)
    parser.add_argument("--train-weight", type=int, default=30)
    parser.add_argument("--plane-weight", type=int, default=20)
    parser.add_argument("--electric-weight", type=int, default=10)
    parser.add_argument(
        "--materialize-json",
        action="store_true",
        help="Also export compatibility JSON files per carrier.",
    )
    return parser.parse_args()


def default_batch_id(args: argparse.Namespace) -> str:
    return f"seed-{args.seed}-{args.start_date}-{args.end_date}-{args.total}"


def main() -> None:
    args = parse_args()
    provider = GeneratedTicketProvider(data_dir=ROOT / "data")
    result = provider.generate(
        GenerationConfig(
            total=args.total,
            start_date=datetime.strptime(args.start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(args.end_date, "%Y-%m-%d"),
            seed=args.seed,
            batch_id=args.batch_id or default_batch_id(args),
            tmp_dir=ROOT / args.tmp_dir,
            materialize_json=args.materialize_json,
            transport_types=tuple(args.transport_types or ()),
            weights={
                "plane": args.plane_weight,
                "train": args.train_weight,
                "bus": args.bus_weight,
                "electric_train": args.electric_weight,
            },
        )
    )
    print(
        f"OK: generated {result.total_generated} tickets in {result.batch_dir} "
        f"(batch={result.batch_id})."
    )


if __name__ == "__main__":
    main()
