from __future__ import annotations

import asyncio
import uuid
from typing import Any

from aeromind.demo.models import CreateOrderBody, OrderSummary, utcnow
from aeromind.demo.pipeline import (
    advance_delivery,
    build_demo_runners,
    current_agent_label,
    initial_demo_state,
    inject_escalation_scenario,
    orchestrator_tick,
    resolve_escalation,
    trigger_workflow,
)


class DemoStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._orders: dict[str, dict[str, Any]] = {}
        self._runners = build_demo_runners()

    def _make_id(self) -> str:
        return f"ORD-{uuid.uuid4().hex[:6].upper()}"

    async def seed_samples(self) -> None:
        async with self._lock:
            if self._orders:
                return
            samples = [
                CreateOrderBody(
                    origin="JFK",
                    destination="LAX",
                    international=False,
                    weight_kg=1800,
                    has_docs=True,
                    route_stays_in_country=True,
                    delay_hours=2.0,
                    hazmat_on_board=False,
                ),
                CreateOrderBody(
                    origin="MIA",
                    destination="LHR",
                    international=True,
                    weight_kg=4200,
                    has_docs=True,
                    route_stays_in_country=True,
                    delay_hours=4.0,
                    hazmat_on_board=False,
                ),
                CreateOrderBody(
                    origin="ORD",
                    destination="SEA",
                    international=False,
                    weight_kg=9200,
                    has_docs=True,
                    route_stays_in_country=True,
                    delay_hours=3.5,
                    hazmat_on_board=True,
                ),
            ]
            meta = [
                ("Northwind Pharma", "Contoso Devices", "Fabrikam Air Cargo"),
                ("Wide World Exports", "Adventure Works Mfg", "Tailspin Cargo"),
                ("Blue Yonder Foods", "Northwind Kitchens", "Contoso Freight"),
            ]
            for body, (ship, mfg, sup) in zip(samples, meta, strict=True):
                oid = self._make_id()
                wf = f"W-{uuid.uuid4().hex[:8]}"
                route = f"{body.origin} → {body.destination}"
                payload = body.model_dump()
                payload["shipper"] = ship
                payload["manufacturer"] = mfg
                payload["supplier"] = sup
                payload["created_at"] = utcnow().isoformat()
                st = initial_demo_state(wf, payload)
                st["order_id"] = oid
                st["route_label"] = route
                self._orders[oid] = st

    async def list_orders(self) -> list[OrderSummary]:
        async with self._lock:
            out: list[OrderSummary] = []
            for oid, st in self._orders.items():
                out.append(
                    OrderSummary(
                        id=oid,
                        route=st.get("route_label") or st["payload"].get("route_label", ""),
                        status=st.get("status") or "READY",
                        current_agent=current_agent_label(st),
                    )
                )
            return sorted(out, key=lambda x: x.id)

    async def create_order(self, body: CreateOrderBody) -> str:
        async with self._lock:
            oid = self._make_id()
            wf = f"W-{uuid.uuid4().hex[:8]}"
            route = f"{body.origin} → {body.destination}"
            payload = body.model_dump()
            payload["shipper"] = "Demo Shipper"
            payload["manufacturer"] = "Demo Manufacturer"
            payload["supplier"] = "Demo Supplier"
            payload["created_at"] = utcnow().isoformat()
            st = initial_demo_state(wf, payload)
            st["order_id"] = oid
            st["route_label"] = route
            self._orders[oid] = st
            return oid

    async def get_raw(self, order_id: str) -> dict[str, Any] | None:
        async with self._lock:
            o = self._orders.get(order_id)
            return dict(o) if o else None

    async def trigger(self, order_id: str) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            trigger_workflow(st)
            return True

    async def step(self, order_id: str) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            await orchestrator_tick(st, self._runners)
            return True

    async def run_all(self, order_id: str) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            for _ in range(24):
                if st.get("open_human_gate"):
                    break
                if st.get("status") == "IN_TRANSIT":
                    break
                if not st.get("pending"):
                    break
                await orchestrator_tick(st, self._runners)
            return True

    async def deliver(self, order_id: str) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            advance_delivery(st)
            return True

    async def inject(self, order_id: str, kind: str) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            inject_escalation_scenario(st, kind)
            return True

    async def resolve(self, order_id: str, action: str, note: str | None) -> bool:
        async with self._lock:
            st = self._orders.get(order_id)
            if not st:
                return False
            resolve_escalation(st, action, note)
            return True


_store: DemoStore | None = None


def get_demo_store() -> DemoStore:
    global _store
    if _store is None:
        _store = DemoStore()
    return _store
