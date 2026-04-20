from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aeromind.demo.models import CreateOrderBody, EscalationActionBody, OrderDetail, OrderSummary, utcnow
from aeromind.demo.pipeline import (
    build_timeline,
    current_agent_label,
    escalation_info,
    shared_state_view,
)
from aeromind.demo.store import get_demo_store


router = APIRouter(prefix="/api/demo", tags=["demo"])


def _serialize_results(agent_results: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in agent_results.items():
        if hasattr(v, "model_dump"):
            out[k] = v.model_dump()
        else:
            out[k] = v
    return out


def _to_detail(st: dict[str, Any]) -> OrderDetail:
    payload = dict(st.get("payload") or {})
    route = st.get("route_label") or f"{payload.get('origin')} → {payload.get('destination')}"
    preview = {
        "international": payload.get("international"),
        "weight_kg": payload.get("weight_kg"),
        "has_docs": payload.get("has_docs"),
        "route_stays_in_country": payload.get("route_stays_in_country"),
        "delay_hours": payload.get("delay_hours"),
        "hazmat_on_board": payload.get("hazmat_on_board"),
        "demo_escalation": payload.get("demo_escalation"),
    }
    return OrderDetail(
        id=st["order_id"],
        route=route,
        origin=str(payload.get("origin", "")),
        destination=str(payload.get("destination", "")),
        shipper=str(payload.get("shipper", "")),
        manufacturer=str(payload.get("manufacturer", "")),
        supplier=str(payload.get("supplier", "")),
        status=st.get("status") or "READY",
        current_agent=current_agent_label(st),
        current_stage=st.get("demo_stage") or "",
        shared_state=shared_state_view(st),
        timeline=build_timeline(st),
        agent_logs=dict(st.get("agent_logs") or {}),
        escalation=escalation_info(st),
        payload_preview=preview,
        agent_results=_serialize_results(dict(st.get("agent_results") or {})),
        workflow_id=st.get("workflow_id", ""),
    )


@router.get("/orders", response_model=list[OrderSummary])
async def list_orders() -> list[OrderSummary]:
    return await get_demo_store().list_orders()


@router.post("/orders", response_model=dict[str, str])
async def create_order(body: CreateOrderBody) -> dict[str, str]:
    oid = await get_demo_store().create_order(body)
    return {"id": oid}


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(order_id: str) -> OrderDetail:
    st = await get_demo_store().get_raw(order_id)
    if not st:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_detail(st)


@router.post("/orders/{order_id}/workflow/trigger")
async def workflow_trigger(order_id: str) -> dict[str, Any]:
    store = get_demo_store()
    ok = await store.trigger(order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


@router.post("/orders/{order_id}/workflow/step")
async def workflow_step(order_id: str) -> dict[str, Any]:
    store = get_demo_store()
    ok = await store.step(order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


@router.post("/orders/{order_id}/workflow/run-all")
async def workflow_run_all(order_id: str) -> dict[str, Any]:
    store = get_demo_store()
    ok = await store.run_all(order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


@router.post("/orders/{order_id}/delivery/complete")
async def delivery_complete(order_id: str) -> dict[str, Any]:
    store = get_demo_store()
    ok = await store.deliver(order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


class InjectBody(BaseModel):
    kind: str  # missing_docs | route | load


@router.post("/orders/{order_id}/escalation/inject")
async def escalation_inject(order_id: str, body: InjectBody) -> dict[str, Any]:
    if body.kind not in ("missing_docs", "route", "load"):
        raise HTTPException(status_code=400, detail="kind must be missing_docs | route | load")
    store = get_demo_store()
    ok = await store.inject(order_id, body.kind)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


@router.post("/orders/{order_id}/escalation/resolve")
async def escalation_resolve(order_id: str, body: EscalationActionBody) -> dict[str, Any]:
    store = get_demo_store()
    ok = await store.resolve(order_id, body.action, body.note)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found")
    st = await store.get_raw(order_id)
    assert st is not None
    return {"ok": True, "order": _to_detail(st).model_dump()}


@router.get("/health")
async def demo_health() -> dict[str, str]:
    return {"status": "ok", "service": "aeromind-demo", "ts": utcnow().isoformat()}
