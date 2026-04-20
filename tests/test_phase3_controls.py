import pytest

from aeromind.agents.impl import build_default_runners
from aeromind.agents.runner import AgentRunners
from aeromind.judge.worker import run_judge_for_workflow
from aeromind.orchestrator.graph import run_orchestration
from aeromind.schemas.agent_io import (
    CargoComplyOutput,
    ClearPathOutput,
    ComplianceStatement,
    RerouteOption,
)
from aeromind.schemas.domain import AgentId, EventType
from aeromind.tools.registry import ToolContext, ToolRegistry


@pytest.mark.asyncio
async def test_dg_lock_zeros_commit_when_not_accepted():
    runners = build_default_runners()

    async def cp(_):
        return ClearPathOutput(
            disruption_summary="reroute needed",
            ranked_options=[
                RerouteOption(
                    route_id="r1",
                    description="via X",
                    transit_delta_hours=2,
                    cost_delta_usd=1000,
                    reliability_score=0.9,
                )
            ],
            booking_commit_requested=True,
            handoff={"reroute_complete": True},
        )

    r = AgentRunners(clearpath=cp, loadiq=runners.loadiq, cargocomply=runners.cargocomply)
    state = await run_orchestration(
        workflow_id="W-dg",
        event_id="E-dg",
        event_type=EventType.WEATHER_ALERT.value,
        payload={
            "cargo_is_dg": True,
            "reroute_new_country": True,
            "dg_accepted": False,
            "zone2_open": True,
            "manifest_item_ids": [],
        },
        runners=r,
        session=None,
    )
    msgs = " ".join(state.get("messages") or [])
    assert "dg_lock_blocked_commit" in msgs
    assert state.get("autonomous_commits") == 0


@pytest.mark.asyncio
async def test_blast_radius_cap_second_wave(monkeypatch):
    from aeromind.orchestrator import graph as g

    monkeypatch.setattr("aeromind.config.settings.blast_radius_cap", 1)

    async def cp(_):
        return ClearPathOutput(
            disruption_summary="x",
            ranked_options=[
                RerouteOption(
                    route_id="r1", description="d", transit_delta_hours=1, cost_delta_usd=1, reliability_score=0.9
                )
            ],
            booking_commit_requested=True,
            handoff={"reroute_complete": True},
        )

    base = build_default_runners()
    r = AgentRunners(clearpath=cp, loadiq=base.loadiq, cargocomply=base.cargocomply)
    state = await g.run_orchestration(
        workflow_id="W-br2",
        event_id="E-br2",
        event_type=EventType.NOTAM_FLAG.value,
        payload={},
        runners=r,
        session=None,
    )
    assert state.get("status") == "BLAST_RADIUS_CAP"
    assert state.get("blast_radius_halt") is True


@pytest.mark.asyncio
async def test_judge_flags_ungrounded():
    cc = CargoComplyOutput(
        status="hold",
        statements=[ComplianceStatement(text="No citation here", source_chunk_id=None)],
    )
    res = await run_judge_for_workflow(
        session=None,
        workflow_id="WJ",
        trace={"payload": {"manifest_item_ids": []}},
        agent_results={"CARGOCOMPLY": cc},
    )
    assert res.mandatory_human_review is True
    assert res.payload.get("ungrounded_compliance")


@pytest.mark.asyncio
async def test_allowlist_blocks_cargocomply_booking():
    from unittest.mock import AsyncMock, MagicMock

    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    reg = ToolRegistry()
    reg.register("booking_write", lambda **kwargs: {"ok": True})
    ctx = ToolContext(
        workflow_id="W1",
        agent_id=AgentId.CARGOCOMPLY,
        session=session,
        open_zone2_or_zone3=False,
        dg_accepted=True,
        cargo_is_dg=False,
        reroute_to_new_country=False,
        autonomous_commits=0,
        blast_radius_cap=15,
    )
    with pytest.raises(PermissionError):
        await reg.call("booking_write", ctx, args={})
    assert session.execute.called
