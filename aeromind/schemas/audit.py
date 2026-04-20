from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aeromind.schemas.domain import AgentId


class TerminalState(str, Enum):
    WORKFLOW_CLOSED_CLEAN = "WORKFLOW_CLOSED_CLEAN"
    ESCALATION_FIRED = "ESCALATION_FIRED"
    WORKFLOW_PAUSED_GATE = "WORKFLOW_PAUSED_GATE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    BLAST_RADIUS_CAP = "BLAST_RADIUS_CAP"
    FAILURE_SURFACED = "FAILURE_SURFACED"


class AuditLogEntry(BaseModel):
    actor: str | AgentId
    decision_payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    outcome: TerminalState | str
    prev_hash: str | None = None
    entry_hash: str | None = None
