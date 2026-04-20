from __future__ import annotations

import json
import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.agents.runner import AgentRunners, run_agent_tick
from aeromind.config import settings
from aeromind.db.repository import AuditRepository
from aeromind.judge.worker import run_judge_for_workflow
from aeromind.orchestrator.routing import first_agents_for_event, followon_after_clearpath
from aeromind.orchestrator.state import OrchState
from aeromind.schemas.domain import AgentId, EventType


def _event_type(value: str) -> EventType:
    return EventType(value)


async def _log_orch_event(session: AsyncSession | None, event_type: str, payload: dict[str, Any]) -> None:
    if session is None:
        return
    eid = payload.get("correlation_id") or str(uuid.uuid4())
    await session.execute(
        text(
            """
            INSERT INTO orchestrator_events (event_id, event_type, payload)
            VALUES (:event_id, :event_type, CAST(:payload AS JSONB))
            ON CONFLICT (event_id) DO NOTHING
            """
        ),
        {
            "event_id": eid,
            "event_type": event_type,
            "payload": json.dumps({**payload, "correlation_id": eid}),
        },
    )
    await session.commit()


async def orchestrator_node(
    state: OrchState,
    *,
    runners: AgentRunners,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Single step: expand routing, run one wave of pending agents, apply guards."""
    updates: dict[str, Any] = {}
    messages = list(state.get("messages") or [])

    if state.get("open_human_gate") or state.get("blast_radius_halt"):
        updates["status"] = state.get("status") or "PAUSED"
        return updates

    workflow_id = state["workflow_id"]
    event_type = _event_type(state["event_type"])
    payload = dict(state.get("payload") or {})

    pending = list(state.get("pending") or [])
    completed = list(state.get("completed") or [])
    results = dict(state.get("agent_results") or {})
    auto_commits = int(state.get("autonomous_commits") or 0)

    reroute_complete_flag = bool(state.get("reroute_complete"))
    dg_accepted = bool(state.get("dg_accepted"))
    cargo_is_dg = bool(payload.get("cargo_is_dg", False))
    reroute_new_country = bool(payload.get("reroute_new_country", False))

    if not pending and not completed:
        manifest_type_changed = bool(payload.get("cargo_type_changed", False))
        pending = [
            a.value
            for a in first_agents_for_event(
                event_type,
                manifest_cargo_type_changed=manifest_type_changed,
                reroute_complete=reroute_complete_flag,
            )
        ]
        messages.append(f"initial_route:{pending}")

    if not pending:
        if event_type in (EventType.WEATHER_ALERT, EventType.NOTAM_FLAG):
            cp = results.get(AgentId.CLEARPATH.value)
            handoff = (getattr(cp, "handoff", None) or {}) if cp else {}
            if handoff.get("reroute_complete"):
                need = [a.value for a in followon_after_clearpath(True)]
                pending = [a for a in need if a not in completed]

        if not pending:
            updates["status"] = "CLOSED_CLEAN"
            updates["messages"] = messages + ["closed"]
            updates["pending"] = []
            updates["completed"] = completed
            updates["agent_results"] = results
            updates["autonomous_commits"] = auto_commits
            return updates

    wave = list(pending)
    pending = []
    for agent_str in wave:
        agent = AgentId(agent_str)
        if agent.value in completed:
            continue

        agent_state = {
            **state,
            "completed": completed,
            "agent_results": results,
            "payload": payload,
            "reroute_complete": reroute_complete_flag,
            "dg_accepted": dg_accepted,
        }
        _, out, meta = await run_agent_tick(agent, agent_state, runners)

        if agent == AgentId.CLEARPATH and meta.get("autonomous_commit"):
            if cargo_is_dg and reroute_new_country and not dg_accepted:
                await _log_orch_event(
                    session,
                    EventType.DG_LOCK_BREACH_ATTEMPT.value,
                    {"workflow_id": workflow_id, "correlation_id": str(uuid.uuid4())},
                )
                messages.append("dg_lock_blocked_commit")
                meta["autonomous_commit"] = 0

        new_commits = int(meta.get("autonomous_commit") or 0)
        if new_commits:
            if auto_commits + new_commits > settings.blast_radius_cap:
                updates["blast_radius_halt"] = True
                updates["status"] = "BLAST_RADIUS_CAP"
                await _log_orch_event(
                    session,
                    EventType.BLAST_RADIUS_CAP.value,
                    {"workflow_id": workflow_id, "correlation_id": str(uuid.uuid4())},
                )
                messages.append("blast_radius_cap")
                updates["messages"] = messages
                updates["pending"] = []
                updates["completed"] = completed
                updates["agent_results"] = results
                updates["autonomous_commits"] = auto_commits
                return updates
            auto_commits += new_commits

        if getattr(out, "escalation_required", False):
            updates["open_human_gate"] = True
            updates["status"] = "AWAITING_HUMAN"

        if agent == AgentId.CARGOCOMPLY and getattr(out, "dg_accepted", False):
            dg_accepted = True
            updates["dg_accepted"] = True

        if agent == AgentId.CLEARPATH and meta.get("reroute_complete"):
            reroute_complete_flag = True
            updates["reroute_complete"] = True
            payload["reroute_handoff"] = getattr(out, "handoff", {}) or {}

        results[agent.value] = out
        completed.append(agent.value)

    if not updates.get("open_human_gate") and not updates.get("blast_radius_halt"):
        if event_type == EventType.NEW_BOOKING:
            if AgentId.LOADIQ.value in completed and AgentId.CARGOCOMPLY.value in completed:
                updates["status"] = "CLOSED_CLEAN"
        elif event_type in (EventType.WEATHER_ALERT, EventType.NOTAM_FLAG):
            if {AgentId.CLEARPATH.value, AgentId.LOADIQ.value, AgentId.CARGOCOMPLY.value}.issubset(set(completed)):
                updates["status"] = "CLOSED_CLEAN"

    updates["pending"] = pending
    updates["completed"] = completed
    updates["agent_results"] = results
    updates["autonomous_commits"] = auto_commits
    updates["messages"] = messages
    return updates


def route_should_continue(state: OrchState) -> Literal["continue", "finish"]:
    if state.get("open_human_gate") or state.get("blast_radius_halt"):
        return "finish"
    if state.get("status") in ("CLOSED_CLEAN",):
        return "finish"

    evt = state.get("event_type")
    completed = state.get("completed") or []
    results = state.get("agent_results") or {}

    if evt in (EventType.WEATHER_ALERT.value, EventType.NOTAM_FLAG.value):
        if AgentId.CLEARPATH.value in completed:
            cp = results.get(AgentId.CLEARPATH.value)
            handoff = (getattr(cp, "handoff", None) or {}) if cp else {}
            if handoff.get("reroute_complete"):
                if AgentId.LOADIQ.value not in completed or AgentId.CARGOCOMPLY.value not in completed:
                    return "continue"
        elif not completed:
            return "continue"
        return "finish"

    if evt == EventType.NEW_BOOKING.value:
        if AgentId.LOADIQ.value in completed and AgentId.CARGOCOMPLY.value in completed:
            return "finish"
        return "continue"

    if state.get("pending"):
        return "continue"
    return "finish"


def build_graph(runners: AgentRunners, session: AsyncSession | None) -> StateGraph:
    graph: StateGraph = StateGraph(OrchState)

    async def tick_fn(s: OrchState) -> dict[str, Any]:
        return await orchestrator_node(s, runners=runners, session=session)

    graph.add_node("tick", tick_fn)
    graph.set_entry_point("tick")
    graph.add_conditional_edges(
        "tick",
        route_should_continue,
        {"continue": "tick", "finish": END},
    )
    return graph


async def run_orchestration(
    *,
    workflow_id: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
    runners: AgentRunners,
    session: AsyncSession | None = None,
) -> OrchState:
    graph = build_graph(runners, session)
    app = graph.compile()

    init: OrchState = {
        "workflow_id": workflow_id,
        "event_id": event_id,
        "event_type": event_type,
        "payload": payload,
        "pending": [],
        "completed": [],
        "agent_results": {},
        "reroute_complete": bool(payload.get("reroute_complete")),
        "dg_accepted": bool(payload.get("dg_accepted")),
        "cargo_is_dg_bool": bool(payload.get("cargo_is_dg")),
        "reroute_new_country": bool(payload.get("reroute_new_country")),
        "open_human_gate": False,
        "blast_radius_halt": False,
        "status": "OPEN",
        "autonomous_commits": 0,
        "messages": [],
    }

    out_state: OrchState = await app.ainvoke(init)

    if session and out_state.get("status") == "CLOSED_CLEAN":
        await AuditRepository.append_entry(
            session,
            workflow_id=workflow_id,
            actor=AgentId.ORCHESTRATOR.value,
            decision_payload={"event_id": event_id, "event_type": event_type},
            evidence_refs=[],
            outcome="WORKFLOW_CLOSED_CLEAN",
        )
        await run_judge_for_workflow(
            session=session,
            workflow_id=workflow_id,
            trace={"payload": payload},
            agent_results=dict(out_state.get("agent_results") or {}),
        )
    return out_state
