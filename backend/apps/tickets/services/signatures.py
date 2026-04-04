from __future__ import annotations

import hashlib
import json


def stable_digest(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_route_signature(
    *,
    from_city: str,
    to_city: str,
    carrier: str,
    transport_type: str,
    is_direct: bool,
) -> str:
    digest = stable_digest(
        {
            "carrier": carrier,
            "from_city": from_city,
            "is_direct": bool(is_direct),
            "to_city": to_city,
            "transport_type": transport_type,
        }
    )
    return f"route-{digest[:32]}"


def build_external_ticket_id(payload: dict) -> str:
    digest = stable_digest(payload)
    return f"ticket-{digest[:40]}"
