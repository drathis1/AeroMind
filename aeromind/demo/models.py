from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DemoStage(str, Enum):
    ORDER_CREATED = "order_created"
    COMPLIANCE = "compliance"
    ROUTING = "routing"
    LOAD_OPT = "load_opt"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class TimelineStep(BaseModel):
    id: str
    label: str
    agent: str | None = None
    lane: str
    status: StepStatus


class SharedStateView(BaseModel):
    current_stage: str
    active_agent: str | None
    completed_agents: list[str]
    escalation_flag: bool
    escalation_reason: str | None = None
    orchestrator_notes: list[str] = Field(default_factory=list)


class EscalationInfo(BaseModel):
    active: bool
    source_agent: str | None = None
    message: str | None = None


class OrderSummary(BaseModel):
    id: str
    route: str
    status: str
    current_agent: str | None


class OrderDetail(BaseModel):
    id: str
    route: str
    origin: str
    destination: str
    shipper: str
    manufacturer: str
    supplier: str
    status: str
    current_agent: str | None
    current_stage: str
    shared_state: SharedStateView
    timeline: list[TimelineStep]
    agent_logs: dict[str, list[str]]
    escalation: EscalationInfo
    payload_preview: dict[str, Any]
    agent_results: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str = ""


class CreateOrderBody(BaseModel):
    origin: str = "JFK"
    destination: str = "LAX"
    international: bool = False
    weight_kg: float = 2400.0
    has_docs: bool = True
    route_stays_in_country: bool = True
    delay_hours: float = 2.0
    hazmat_on_board: bool = False


class EscalationActionBody(BaseModel):
    action: Literal["approve", "resolve", "override"]
    note: str | None = None
