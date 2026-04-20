import pytest

from aeromind.agents.impl import build_default_runners
from aeromind.orchestrator.graph import run_orchestration
from aeromind.schemas.domain import EventType


@pytest.mark.asyncio
async def test_new_booking_closes_clean_without_db():
    runners = build_default_runners()
    state = await run_orchestration(
        workflow_id="W-test-1",
        event_id="E-1",
        event_type=EventType.NEW_BOOKING.value,
        payload={"manifest_item_ids": ["A1", "A2"]},
        runners=runners,
        session=None,
    )
    assert state.get("status") == "CLOSED_CLEAN"
    assert "LOADIQ" in (state.get("completed") or [])
    assert "CARGOCOMPLY" in (state.get("completed") or [])


@pytest.mark.asyncio
async def test_weather_two_phase_routing():
    runners = build_default_runners()
    state = await run_orchestration(
        workflow_id="W-test-2",
        event_id="E-2",
        event_type=EventType.WEATHER_ALERT.value,
        payload={},
        runners=runners,
        session=None,
    )
    completed = state.get("completed") or []
    assert "CLEARPATH" in completed
    assert "LOADIQ" in completed
    assert "CARGOCOMPLY" in completed
