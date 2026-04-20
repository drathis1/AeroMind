from __future__ import annotations

from typing import Any

from aeromind.schemas.domain import EventType


def simulate_bulk_notam(*, affected_bookings: int) -> dict[str, Any]:
    return {
        "notam_text": f"Closure corridor X affecting {affected_bookings} active bookings",
        "bulk_notam": True,
        "affected_bookings": affected_bookings,
        "corridor": "X",
    }


def simulate_new_bookings(count: int) -> list[dict[str, Any]]:
    return [
        {
            "booking_id": f"B-{i}",
            "manifest_item_ids": [f"C-{i}"],
            "value_usd": 10_000 + i,
        }
        for i in range(count)
    ]


def booking_storm_threshold(raw: dict[str, Any]) -> bool:
    return float(raw.get("hours_to_departure", 99)) <= 14


def notam_affects_active(raw: dict[str, Any]) -> bool:
    return int(raw.get("affected_bookings", 0)) > 0


def to_event_type_manifest() -> EventType:
    return EventType.MANIFEST_CHANGE
