from __future__ import annotations

from aeromind.config import settings
from aeromind.schemas.domain import AgentId, EventType


def first_agents_for_event(
    event_type: EventType,
    *,
    manifest_cargo_type_changed: bool,
    reroute_complete: bool,
) -> list[AgentId]:
    """Section 3.2 routing — first activation."""
    if event_type in (EventType.WEATHER_ALERT, EventType.NOTAM_FLAG):
        return [AgentId.CLEARPATH]
    if event_type == EventType.NEW_BOOKING:
        return [AgentId.LOADIQ, AgentId.CARGOCOMPLY]
    if event_type == EventType.MANIFEST_CHANGE:
        if manifest_cargo_type_changed:
            return [AgentId.LOADIQ, AgentId.CARGOCOMPLY]
        return [AgentId.LOADIQ]
    if event_type == EventType.REROUTE_CONFIRMED and reroute_complete:
        return [AgentId.LOADIQ, AgentId.CARGOCOMPLY]
    if event_type in (EventType.MANUAL_TRIGGER, EventType.ESCALATION_RESOLVED, EventType.HUMAN_GATE_RESPONSE):
        return []  # filled from payload by orchestrator
    return []


def followon_after_clearpath(state_reroute_complete: bool) -> list[AgentId]:
    if state_reroute_complete:
        return [AgentId.LOADIQ, AgentId.CARGOCOMPLY]
    return []


def zone_for_shipment_value(value_usd: float) -> str:
    if value_usd >= settings.gate_value_usd:
        return "ZONE_2_GATED"
    return "ZONE_1_FULL"
