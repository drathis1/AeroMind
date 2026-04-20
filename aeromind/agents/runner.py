from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aeromind.schemas.agent_io import CargoComplyOutput, ClearPathOutput, LoadIQOutput
from aeromind.schemas.domain import AgentId


@dataclass
class AgentRunners:
    clearpath: Callable[[dict[str, Any]], Awaitable[ClearPathOutput]]
    loadiq: Callable[[dict[str, Any]], Awaitable[LoadIQOutput]]
    cargocomply: Callable[[dict[str, Any]], Awaitable[CargoComplyOutput]]


async def run_agent_tick(
    agent: AgentId,
    state: dict[str, Any],
    runners: AgentRunners,
) -> tuple[AgentId, Any, dict[str, Any]]:
    """Run one agent; return agent id, output model, side-effect metadata (commits, flags)."""
    meta: dict[str, Any] = {"autonomous_commit": 0, "reroute_complete": False, "dg_accepted": False}
    payload = dict(state.get("payload") or {})

    if agent == AgentId.CLEARPATH:
        out = await runners.clearpath(
            {
                "workflow_id": state["workflow_id"],
                "event_type": state.get("event_type"),
                "payload": payload,
            }
        )
        if out.booking_commit_requested:
            meta["autonomous_commit"] = 1
        meta["reroute_complete"] = bool(out.handoff.get("reroute_complete"))
        return agent, out, meta

    if agent == AgentId.LOADIQ:
        out = await runners.loadiq(
            {
                "workflow_id": state["workflow_id"],
                "event_type": state.get("event_type"),
                "payload": payload,
            }
        )
        if out.ground_crew_notify_requested:
            meta["autonomous_commit"] = 1
        return agent, out, meta

    if agent == AgentId.CARGOCOMPLY:
        out = await runners.cargocomply(
            {
                "workflow_id": state["workflow_id"],
                "event_type": state.get("event_type"),
                "payload": payload,
            }
        )
        meta["dg_accepted"] = bool(out.dg_accepted)
        return agent, out, meta

    raise ValueError(f"unknown agent {agent}")
