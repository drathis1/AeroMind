from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentId(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    LOADIQ = "LOADIQ"
    CLEARPATH = "CLEARPATH"
    CARGOCOMPLY = "CARGOCOMPLY"


class EventType(str, Enum):
    WEATHER_ALERT = "WEATHER_ALERT"
    NOTAM_FLAG = "NOTAM_FLAG"
    NEW_BOOKING = "NEW_BOOKING"
    MANIFEST_CHANGE = "MANIFEST_CHANGE"
    REROUTE_CONFIRMED = "REROUTE_CONFIRMED"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"
    ESCALATION_RESOLVED = "ESCALATION_RESOLVED"
    HUMAN_GATE_RESPONSE = "HUMAN_GATE_RESPONSE"
    BLAST_RADIUS_CAP = "BLAST_RADIUS_CAP"
    DG_LOCK_BREACH_ATTEMPT = "DG_LOCK_BREACH_ATTEMPT"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"


class WorkflowStatus(str, Enum):
    OPEN = "OPEN"
    AWAITING_AGENTS = "AWAITING_AGENTS"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    BLAST_RADIUS_PAUSED = "BLAST_RADIUS_PAUSED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    CLOSED_CLEAN = "CLOSED_CLEAN"
    CLOSED_ESCALATION = "CLOSED_ESCALATION"
    CLOSED_FAILURE = "CLOSED_FAILURE"


class AutonomyZone(str, Enum):
    ZONE_1_FULL = "ZONE_1_FULL"
    ZONE_2_GATED = "ZONE_2_GATED"
    ZONE_3_HARD_STOP = "ZONE_3_HARD_STOP"


class EscalationFlag(str, Enum):
    NONE = "NONE"
    VALUE_GATE = "VALUE_GATE"
    MULTI_COUNTRY = "MULTI_COUNTRY"
    UNSOLVABLE_LOAD = "UNSOLVABLE_LOAD"
    SANCTIONS = "SANCTIONS"
    NO_VIABLE_ROUTE = "NO_VIABLE_ROUTE"
    UNGROUNDED_COMPLIANCE = "UNGROUNDED_COMPLIANCE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    DG_PENDING = "DG_PENDING"
    OTHER = "OTHER"


class OrchestratorEvent(BaseModel):
    event_id: str
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class WorkflowState(BaseModel):
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.OPEN
    event_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    open_escalation: bool = False
    reroute_complete: bool = False
    dg_accepted: bool = False
    autonomous_commits_this_event: int = 0
    crew_notify_queued: bool = False
    zone_flags: list[AutonomyZone] = Field(default_factory=list)
    pending_agents: list[str] = Field(default_factory=list)
    completed_agents: list[str] = Field(default_factory=list)
    escalation_flags: list[EscalationFlag] = Field(default_factory=list)
