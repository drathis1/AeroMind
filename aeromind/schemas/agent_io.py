from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RerouteOption(BaseModel):
    route_id: str
    description: str
    transit_delta_hours: float
    cost_delta_usd: float
    reliability_score: float  # 0-1 higher better


class ClearPathOutput(BaseModel):
    disruption_summary: str
    ranked_options: list[RerouteOption] = Field(default_factory=list)
    selected_option_id: str | None = None
    booking_commit_requested: bool = False
    shipper_notified: bool = False
    handoff: dict[str, Any] = Field(default_factory=dict)
    escalation_required: bool = False
    escalation_reason: str | None = None
    ground_truth_ranked_for_judge: list[RerouteOption] = Field(default_factory=list)


class ULDPlacement(BaseModel):
    cargo_item_id: str
    uld_position: str


class LoadIQOutput(BaseModel):
    placements: list[ULDPlacement] = Field(default_factory=list)
    weight_balance_ok: bool = False
    hazmat_conflicts: list[str] = Field(default_factory=list)
    crew_instructions: str = ""
    ground_crew_notify_requested: bool = False
    escalation_required: bool = False
    escalation_reason: str | None = None
    manifest_item_ids_in: list[str] = Field(default_factory=list)


class ComplianceStatement(BaseModel):
    text: str
    source_chunk_id: str | None = None


class CargoComplyOutput(BaseModel):
    status: str  # pass | flag | hold
    statements: list[ComplianceStatement] = Field(default_factory=list)
    missing_docs: list[str] = Field(default_factory=list)
    dg_accepted: bool = False
    handoff_route_key: str | None = None
    escalation_required: bool = False
    escalation_reason: str | None = None
