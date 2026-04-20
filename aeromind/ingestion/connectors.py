"""Stub connectors — replace with live weather / NOTAM / booking clients."""

from __future__ import annotations

from typing import Any


async def fetch_weather_stub(corr_id: str) -> dict[str, Any]:
    return {"correlation_id": corr_id, "hours_to_departure": 10, "severity": "high"}


async def fetch_notam_stub(corr_id: str) -> dict[str, Any]:
    return {"correlation_id": corr_id, "affected_bookings": 3, "notam_text": "RWY closed"}
