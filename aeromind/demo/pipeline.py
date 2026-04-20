from __future__ import annotations

import uuid
from typing import Any

from aeromind.agents.runner import AgentRunners, run_agent_tick
from aeromind.demo.models import DemoStage, EscalationInfo, SharedStateView, StepStatus, TimelineStep, utcnow
from aeromind.schemas.domain import AgentId


def build_demo_runners() -> AgentRunners:
    """Demo agents: simplified rules, no LLM. Agents only read/write via orchestrator-provided state."""

    async def cargocomply(inp: dict[str, Any]) -> Any:
        from aeromind.schemas.agent_io import CargoComplyOutput, ComplianceStatement

        payload = dict(inp.get("payload") or {})
        international = bool(payload.get("international", False))
        has_docs = bool(payload.get("has_docs", True))
        force = payload.get("demo_escalation") == "missing_docs"
        if international and (not has_docs or force):
            return CargoComplyOutput(
                status="hold",
                statements=[
                    ComplianceStatement(
                        text="International lane requires customs documentation.",
                        source_chunk_id="DEMO_IATA_2024",
                    )
                ],
                missing_docs=["Commercial invoice", "Shipper's declaration"],
                dg_accepted=False,
                escalation_required=True,
                escalation_reason="Missing required customs documents for international routing.",
            )
        return CargoComplyOutput(
            status="pass",
            statements=[
                ComplianceStatement(
                    text="Documentation and DG classification acceptable for planned lane.",
                    source_chunk_id="DEMO_REG_OK",
                )
            ],
            missing_docs=[],
            dg_accepted=True,
            escalation_required=False,
        )

    async def clearpath(inp: dict[str, Any]) -> Any:
        from aeromind.schemas.agent_io import ClearPathOutput, RerouteOption

        payload = dict(inp.get("payload") or {})
        stays = bool(payload.get("route_stays_in_country", True))
        delay = float(payload.get("delay_hours", 0.0))
        force = payload.get("demo_escalation") == "route"
        origin = str(payload.get("origin", "ORG"))
        dest = str(payload.get("destination", "DST"))
        if force or not stays or delay >= 6.0:
            return ClearPathOutput(
                disruption_summary="Route constraints violated: cross-border or excessive delay.",
                ranked_options=[],
                selected_option_id=None,
                booking_commit_requested=False,
                handoff={"reroute_complete": False},
                escalation_required=True,
                escalation_reason="Route must remain domestic with delay under 6 hours.",
            )
        opts = [
            RerouteOption(
                route_id="cp-demo-1",
                description=f"{origin} → {dest} (primary)",
                transit_delta_hours=delay,
                cost_delta_usd=0,
                reliability_score=0.95,
            ),
            RerouteOption(
                route_id="cp-demo-2",
                description=f"{origin} → {dest} (alt)",
                transit_delta_hours=delay + 1.0,
                cost_delta_usd=400,
                reliability_score=0.88,
            ),
            RerouteOption(
                route_id="cp-demo-3",
                description=f"{origin} → {dest} (backup)",
                transit_delta_hours=delay + 2.5,
                cost_delta_usd=900,
                reliability_score=0.80,
            ),
        ]
        return ClearPathOutput(
            disruption_summary="Corridor clear; optimal domestic route selected.",
            ranked_options=opts,
            selected_option_id="cp-demo-1",
            booking_commit_requested=True,
            handoff={"reroute_complete": True, "new_country": False},
            escalation_required=False,
        )

    async def loadiq(inp: dict[str, Any]) -> Any:
        from aeromind.schemas.agent_io import LoadIQOutput, ULDPlacement

        payload = dict(inp.get("payload") or {})
        weight = float(payload.get("weight_kg", 0.0))
        haz = bool(payload.get("hazmat_on_board", False))
        force = payload.get("demo_escalation") == "load"
        conflicts: list[str] = []
        if haz:
            conflicts.append("UN-class hazard proximity conflict in main deck plan")
        if force or weight >= 10_000 or conflicts:
            return LoadIQOutput(
                placements=[],
                weight_balance_ok=False,
                hazmat_conflicts=conflicts,
                crew_instructions="Hold load plan pending resolution.",
                ground_crew_notify_requested=False,
                escalation_required=True,
                escalation_reason="Weight limit or hazardous material conflict.",
            )
        return LoadIQOutput(
            placements=[ULDPlacement(cargo_item_id="ULD-1", uld_position="MAIN-2A")],
            weight_balance_ok=True,
            hazmat_conflicts=[],
            crew_instructions="Load per optimized plan; no hazmat conflicts.",
            ground_crew_notify_requested=True,
            escalation_required=False,
        )

    return AgentRunners(clearpath=clearpath, loadiq=loadiq, cargocomply=cargocomply)


AGENT_SEQUENCE: list[str] = [
    AgentId.CARGOCOMPLY.value,
    AgentId.CLEARPATH.value,
    AgentId.LOADIQ.value,
]


def _append_log(logs: dict[str, list[str]], agent: str, line: str) -> None:
    logs.setdefault(agent, []).append(f"[{utcnow().isoformat()}] {line}")


def _orch_note(state: dict[str, Any], line: str) -> None:
    state.setdefault("orchestrator_notes", []).append(f"[{utcnow().isoformat()}] {line}")


def _stage_for_next_agent(next_agent: str) -> str:
    if next_agent == AgentId.CARGOCOMPLY.value:
        return DemoStage.COMPLIANCE.value
    if next_agent == AgentId.CLEARPATH.value:
        return DemoStage.ROUTING.value
    if next_agent == AgentId.LOADIQ.value:
        return DemoStage.LOAD_OPT.value
    return DemoStage.ORDER_CREATED.value


async def orchestrator_tick(state: dict[str, Any], runners: AgentRunners) -> None:
    """
    Central orchestrator: runs exactly one agent invocation, then schedules the next agent via shared state.
    Agents never call each other — only this function invokes run_agent_tick.
    """
    if state.get("open_human_gate"):
        return

    pending = list(state.get("pending") or [])
    completed = list(state.get("completed") or [])
    results = dict(state.get("agent_results") or {})
    payload = dict(state.get("payload") or {})

    if not pending:
        return

    agent_str = pending[0]
    agent = AgentId(agent_str)
    workflow_id = state["workflow_id"]
    _orch_note(state, f"Dispatching {agent_str} for workflow {workflow_id} (agents do not inter-communicate).")

    agent_state = {
        **state,
        "completed": completed,
        "agent_results": results,
        "payload": payload,
    }
    _, out, _meta = await run_agent_tick(agent, agent_state, runners)

    results[agent.value] = out
    completed.append(agent.value)
    pending = pending[1:]

    state["agent_results"] = results
    state["completed"] = completed
    state["pending"] = pending

    if getattr(out, "escalation_required", False):
        state["open_human_gate"] = True
        state["status"] = "AWAITING_HUMAN"
        reason = getattr(out, "escalation_reason", None) or "Agent requested human review."
        state["escalation_reason"] = reason
        _append_log(state["agent_logs"], agent_str, f"Escalation raised: {reason}")
        return

    _append_log(state["agent_logs"], agent_str, _success_log_line(agent, out))
    _append_demo_success_logs(state["agent_logs"], agent, out)

    if not pending:
        for a in AGENT_SEQUENCE:
            if a not in completed:
                state["pending"] = [a]
                state["demo_stage"] = _stage_for_next_agent(a)
                break
        else:
            if set(AGENT_SEQUENCE).issubset(set(completed)):
                state["demo_stage"] = DemoStage.IN_TRANSIT.value
                state["status"] = "IN_TRANSIT"
                _orch_note(state, "All agents completed; releasing to supplier execution lane.")


def _success_log_line(agent: AgentId, out: Any) -> str:
    if agent == AgentId.CARGOCOMPLY:
        return f"Compliance status={getattr(out, 'status', 'ok')}."
    if agent == AgentId.CLEARPATH:
        n = len(getattr(out, "ranked_options", []) or [])
        return f"Ranked {n} route option(s); selected={getattr(out, 'selected_option_id', None)}."
    if agent == AgentId.LOADIQ:
        return f"Placements={len(getattr(out, 'placements', []) or [])}; weight_ok={getattr(out, 'weight_balance_ok', False)}."
    return "Completed."


def _append_demo_success_logs(logs: dict[str, list[str]], agent: AgentId, out: Any) -> None:
    if agent == AgentId.CARGOCOMPLY:
        _append_log(logs, AgentId.CARGOCOMPLY.value, "Checked customs requirements")
        if getattr(out, "missing_docs", None):
            _append_log(logs, AgentId.CARGOCOMPLY.value, "Missing document detected")
    elif agent == AgentId.CLEARPATH:
        n = len(getattr(out, "ranked_options", []) or [])
        _append_log(logs, AgentId.CLEARPATH.value, f"Generated {n} route options")
        _append_log(logs, AgentId.CLEARPATH.value, "Selected optimal route")
    elif agent == AgentId.LOADIQ:
        _append_log(logs, AgentId.LOADIQ.value, "Optimized cargo placement")


def initial_demo_state(workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "event_id": str(uuid.uuid4()),
        "event_type": "NEW_BOOKING",
        "payload": payload,
        "pending": [],
        "completed": [],
        "agent_results": {},
        "open_human_gate": False,
        "blast_radius_halt": False,
        "status": "READY",
        "autonomous_commits": 0,
        "messages": [],
        "demo_stage": DemoStage.ORDER_CREATED.value,
        "agent_logs": {
            AgentId.CARGOCOMPLY.value: [],
            AgentId.CLEARPATH.value: [],
            AgentId.LOADIQ.value: [],
        },
        "orchestrator_notes": [],
        "escalation_reason": None,
    }


def trigger_workflow(state: dict[str, Any]) -> None:
    if state.get("demo_stage") != DemoStage.ORDER_CREATED.value:
        return
    if state.get("status") != "READY":
        return
    state["pending"] = [AgentId.CARGOCOMPLY.value]
    state["status"] = "RUNNING"
    state["demo_stage"] = DemoStage.COMPLIANCE.value
    _orch_note(state, "Order event ingested; queued CargoComply (compliance first).")


def advance_delivery(state: dict[str, Any]) -> None:
    """Human/system handoff: supplier → manufacturer."""
    if state.get("demo_stage") != DemoStage.IN_TRANSIT.value:
        return
    if state.get("status") != "IN_TRANSIT":
        return
    state["demo_stage"] = DemoStage.DELIVERED.value
    state["status"] = "DELIVERED"
    _orch_note(state, "Delivery confirmed at manufacturer; workflow closed (demo).")


def _agent_timeline_status(state: dict[str, Any], agent_id: str) -> StepStatus:
    completed = list(state.get("completed") or [])
    pending = list(state.get("pending") or [])
    open_gate = bool(state.get("open_human_gate"))
    status = state.get("status") or "READY"
    running_agent = pending[0] if pending and status == "RUNNING" else None
    res = (state.get("agent_results") or {}).get(agent_id)

    if agent_id in completed:
        if open_gate and res and getattr(res, "escalation_required", False):
            return StepStatus.FAILED
        return StepStatus.DONE
    if running_agent == agent_id:
        return StepStatus.RUNNING
    return StepStatus.PENDING


def build_timeline(state: dict[str, Any]) -> list[TimelineStep]:
    stage = state.get("demo_stage") or DemoStage.ORDER_CREATED.value
    cc = AgentId.CARGOCOMPLY.value
    cp = AgentId.CLEARPATH.value
    lq = AgentId.LOADIQ.value

    def transit_step() -> StepStatus:
        if stage == DemoStage.DELIVERED.value:
            return StepStatus.DONE
        if stage == DemoStage.IN_TRANSIT.value:
            return StepStatus.RUNNING
        return StepStatus.PENDING

    def delivered_step() -> StepStatus:
        return StepStatus.DONE if stage == DemoStage.DELIVERED.value else StepStatus.PENDING

    return [
        TimelineStep(
            id="created",
            label="Order Created",
            agent=None,
            lane="Shipper",
            status=StepStatus.DONE,
        ),
        TimelineStep(
            id="comply",
            label="Compliance Check",
            agent="CargoComply",
            lane="CargoComply",
            status=_agent_timeline_status(state, cc),
        ),
        TimelineStep(
            id="route",
            label="Route Planning",
            agent="ClearPath",
            lane="ClearPath",
            status=_agent_timeline_status(state, cp),
        ),
        TimelineStep(
            id="load",
            label="Load Optimization",
            agent="LoadIQ",
            lane="LoadIQ",
            status=_agent_timeline_status(state, lq),
        ),
        TimelineStep(
            id="transit",
            label="Shipment Execution",
            agent=None,
            lane="Supplier",
            status=transit_step(),
        ),
        TimelineStep(
            id="done",
            label="Delivered",
            agent=None,
            lane="Manufacturer",
            status=delivered_step(),
        ),
    ]


def shared_state_view(state: dict[str, Any]) -> SharedStateView:
    pending = list(state.get("pending") or [])
    st = state.get("status") or ""
    active: str | None = pending[0] if pending and st == "RUNNING" else None
    if st == "AWAITING_HUMAN":
        active = "ORCHESTRATOR"
    return SharedStateView(
        current_stage=state.get("demo_stage") or "unknown",
        active_agent=active,
        completed_agents=list(state.get("completed") or []),
        escalation_flag=bool(state.get("open_human_gate")),
        escalation_reason=state.get("escalation_reason"),
        orchestrator_notes=list(state.get("orchestrator_notes") or []),
    )


def escalation_info(state: dict[str, Any]) -> EscalationInfo:
    if not state.get("open_human_gate"):
        return EscalationInfo(active=False)
    completed = list(state.get("completed") or [])
    source = completed[-1] if completed else None
    return EscalationInfo(
        active=True,
        source_agent=source,
        message=state.get("escalation_reason"),
    )


def inject_escalation_scenario(state: dict[str, Any], kind: str) -> None:
    """Before the next agent run, force a demo escalation path (missing_docs | route | load)."""
    payload = dict(state.get("payload") or {})
    payload["demo_escalation"] = kind
    state["payload"] = payload
    _orch_note(state, f"Injected escalation scenario: {kind} (will apply on next agent tick).")


def resolve_escalation(state: dict[str, Any], action: str, note: str | None) -> None:
    if not state.get("open_human_gate"):
        return
    completed = list(state.get("completed") or [])
    if not completed:
        return
    last = completed[-1]
    payload = dict(state.get("payload") or {})

    if action == "approve":
        if last == AgentId.CARGOCOMPLY.value:
            payload["has_docs"] = True
        elif last == AgentId.CLEARPATH.value:
            payload["route_stays_in_country"] = True
            payload["delay_hours"] = 2.0
        elif last == AgentId.LOADIQ.value:
            payload["weight_kg"] = min(float(payload.get("weight_kg", 0)), 9999.0)
            payload["hazmat_on_board"] = False
    elif action == "resolve":
        payload["has_docs"] = True
        payload["demo_escalation"] = None
    elif action == "override":
        payload["has_docs"] = True
        payload["route_stays_in_country"] = True
        payload["delay_hours"] = 2.0
        payload["weight_kg"] = min(float(payload.get("weight_kg", 0)), 9999.0)
        payload["hazmat_on_board"] = False

    payload["demo_escalation"] = None
    state["payload"] = payload
    state["completed"] = completed[:-1]
    results = dict(state.get("agent_results") or {})
    results.pop(last, None)
    state["agent_results"] = results
    state["open_human_gate"] = False
    state["escalation_reason"] = None
    state["pending"] = [last]
    state["status"] = "RUNNING"
    _orch_note(state, f"Human gate {action}: {note or 'no note'} — re-queued {last}.")


def current_agent_label(state: dict[str, Any]) -> str | None:
    st = state.get("status") or ""
    if st == "AWAITING_HUMAN":
        return "Orchestrator (human gate)"
    pending = list(state.get("pending") or [])
    if pending and st == "RUNNING":
        aid = pending[0]
        return {"CARGOCOMPLY": "CargoComply", "CLEARPATH": "ClearPath", "LOADIQ": "LoadIQ"}.get(aid, aid)
    if state.get("demo_stage") == DemoStage.IN_TRANSIT.value:
        return "Supplier"
    if state.get("demo_stage") == DemoStage.DELIVERED.value:
        return "Manufacturer"
    return None
