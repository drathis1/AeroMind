from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.agents.impl import build_default_runners
from aeromind.agents.runner import AgentRunners
from aeromind.db.session import SessionLocal
from aeromind.demo.api import router as demo_router
from aeromind.demo.store import get_demo_store
from aeromind.orchestrator.graph import run_orchestration
from aeromind.schemas.domain import AgentId
from aeromind.tools.registry import ToolContext, ToolRegistry


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


app = FastAPI(title="AeroMind Ops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo_router)


@app.on_event("startup")
async def _seed_demo_orders() -> None:
    await get_demo_store().seed_samples()


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "aeromind",
        "docs": "/docs",
        "run_workflow_post": "/v1/workflows/run",
        "workflow_trace_get": "/v1/workflows/{workflow_id}/trace",
        "demo_ui": "Run Next.js in web/ (npm run dev) — multi-agent demo at /api/demo/orders",
        "hint": "Open /docs or POST JSON to /v1/workflows/run",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class GateResolve(BaseModel):
    workflow_id: str
    approve: bool
    rationale: str | None = Field(default=None, min_length=20)


class RunWorkflowBody(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/workflows/run")
async def run_workflow(body: RunWorkflowBody, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    workflow_id = f"W-{uuid.uuid4().hex[:8]}"
    event_id = str(uuid.uuid4())
    runners: AgentRunners = build_default_runners()
    state = await run_orchestration(
        workflow_id=workflow_id,
        event_id=event_id,
        event_type=body.event_type,
        payload=body.payload,
        runners=runners,
        session=session,
    )
    return {"workflow_id": workflow_id, "state": _serialize_state(state)}


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    out = dict(state)
    ar = out.get("agent_results") or {}
    serial = {}
    for k, v in ar.items():
        if hasattr(v, "model_dump"):
            serial[k] = v.model_dump()
        else:
            serial[k] = v
    out["agent_results"] = serial
    return out


@app.get("/v1/workflows/{workflow_id}/trace")
async def workflow_trace(workflow_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    res = await session.execute(
        text(
            """
            SELECT id, actor, decision_payload, evidence_refs, outcome, entry_hash, created_at
            FROM audit_log WHERE workflow_id = :wf ORDER BY id ASC
            """
        ),
        {"wf": workflow_id},
    )
    rows = [dict(r) for r in res.mappings().all()]
    return {"workflow_id": workflow_id, "audit": rows}


@app.get("/v1/workflows/trace/{workflow_id}")
async def workflow_trace_alt(workflow_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Same as GET /v1/workflows/{workflow_id}/trace (common typo convenience)."""
    return await workflow_trace(workflow_id, session)


@app.get("/v1/gates")
async def list_gates(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    res = await session.execute(
        text("SELECT * FROM human_gates WHERE status = 'open' ORDER BY id DESC LIMIT 100")
    )
    return {"gates": [dict(r) for r in res.mappings().all()]}


@app.post("/v1/gates/resolve")
async def resolve_gate(body: GateResolve, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if not body.approve and (not body.rationale or len(body.rationale) < 20):
        raise HTTPException(status_code=400, detail="rationale required (min 20 chars) for deny")
    await session.execute(
        text(
            """
            UPDATE human_gates SET status = :st, rationale = :rat, resolved_at = now()
            WHERE workflow_id = :wf AND status = 'open'
            """
        ),
        {"st": "approved" if body.approve else "denied", "rat": body.rationale, "wf": body.workflow_id},
    )
    await session.commit()
    return {"ok": True}


@app.get("/v1/bulk-review/{workflow_id}")
async def bulk_review(workflow_id: str) -> dict[str, Any]:
    """Bulk-review card payload when blast-radius pauses — store pending in workflow state in prod."""
    return {
        "workflow_id": workflow_id,
        "message": "Workflow paused pending ops bulk approval after blast-radius cap.",
        "actions": [],
    }


@app.post("/v1/dev/tool-try")
async def dev_tool_try(
    workflow_id: str = Query(...),
    agent_id: str = Query(...),
    tool_name: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Demonstrate allowlist violation logging (e.g. CargoComply booking_write)."""

    reg = ToolRegistry()
    reg.register("booking_write", lambda **kwargs: {"ok": True})

    ctx = ToolContext(
        workflow_id=workflow_id,
        agent_id=AgentId(agent_id),
        session=session,
        open_zone2_or_zone3=False,
        dg_accepted=False,
        cargo_is_dg=False,
        reroute_to_new_country=False,
        autonomous_commits=0,
        blast_radius_cap=15,
    )
    try:
        await reg.call(tool_name, ctx, args={})
        return {"allowed": True}
    except PermissionError as e:
        return {"allowed": False, "reason": str(e)}


@app.get("/v1/governance/metrics")
async def governance_metrics(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Uses views from aeromind/db/sql/002_governance_views.sql when applied."""
    out: dict[str, Any] = {}
    for view in ("v_governance_blast_radius", "v_governance_dg_breaches", "v_tool_violation_rate"):
        try:
            res = await session.execute(text(f"SELECT * FROM {view}"))
            out[view] = [dict(r) for r in res.mappings().all()]
        except Exception:
            out[view] = []
    res = await session.execute(
        text(
            """
            SELECT workflow_id, mandatory_human_review, payload, created_at
            FROM llm_judge_evaluations ORDER BY id DESC LIMIT 50
            """
        )
    )
    out["recent_judge_evaluations"] = [dict(r) for r in res.mappings().all()]
    return out


@app.get("/v1/governance/violations")
async def governance_violations(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    res = await session.execute(
        text("SELECT * FROM governance_violations ORDER BY id DESC LIMIT 200")
    )
    rows = []
    for r in res.mappings().all():
        d = dict(r)
        if isinstance(d.get("detail"), str):
            d["detail"] = json.loads(d["detail"])
        rows.append(d)
    return {"violations": rows}
