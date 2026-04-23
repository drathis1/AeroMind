"""Agent-runner builders that vary by ablation configuration.

The original `aeromind.agents.impl.build_default_runners` calls
`sanitize_external_text` inline, so the injection filter is part of the
agent layer. To ablate it we provide a parallel builder that takes an
`enable_injection_filter` flag and an `InjectionRecorder`.

This is the only intentional duplication of `aeromind/agents/impl.py` in the
experiment harness. We keep it deliberately small (delegate logic to the
real schemas) and document why in the methodology.
"""

from __future__ import annotations

from typing import Any

from aeromind.agents.runner import AgentRunners
from aeromind.injection.filter import sanitize_external_text
from aeromind.schemas.agent_io import (
    CargoComplyOutput,
    ClearPathOutput,
    ComplianceStatement,
    LoadIQOutput,
    RerouteOption,
    ULDPlacement,
)

from eval.metrics.instrumentation import InjectionRecorder


def build_runners(
    *,
    enable_injection_filter: bool,
    injection_recorder: InjectionRecorder,
) -> AgentRunners:
    """Build deterministic-mock runners with an explicit injection-filter flag.

    When `enable_injection_filter` is True (A0), each external-text input is
    sanitized and the recorder counts every call. When False (A1, A2), the
    sanitizer is bypassed entirely — external text passes through unchanged.
    """

    def _sanitize(text: str, source: str) -> str:
        if not enable_injection_filter:
            # Filter ablated; record nothing because nothing fired.
            return text
        rep = sanitize_external_text(text, source=source)
        injection_recorder.record(flagged=rep.flagged, pattern=rep.pattern)
        return rep.redacted_text

    async def clearpath(inp: dict[str, Any]) -> ClearPathOutput:
        payload = dict(inp.get("payload") or {})
        payload["notam_text"] = _sanitize(str(payload.get("notam_text", "")), "notam")
        options = [
            RerouteOption(
                route_id="r1",
                description="via AMS",
                transit_delta_hours=2.0,
                cost_delta_usd=1500,
                reliability_score=0.9,
            ),
            RerouteOption(
                route_id="r2",
                description="direct alternate",
                transit_delta_hours=5.0,
                cost_delta_usd=800,
                reliability_score=0.75,
            ),
        ]
        return ClearPathOutput(
            disruption_summary=(
                "NOTAM affecting corridor"
                if payload.get("bulk_notam")
                else "Weather caution"
            ),
            ranked_options=options,
            ground_truth_ranked_for_judge=list(options),
            selected_option_id="r1",
            booking_commit_requested=bool(payload.get("autonomous_booking_ok", True)),
            shipper_notified=False,
            handoff={
                "reroute_complete": True,
                "new_country": bool(payload.get("reroute_new_country", False)),
            },
            escalation_required=bool(payload.get("force_escalation", False)),
        )

    async def loadiq(inp: dict[str, Any]) -> LoadIQOutput:
        payload = dict(inp.get("payload") or {})
        payload["manifest_notes"] = _sanitize(
            str(payload.get("manifest_notes", "")), "manifest"
        )
        manifest_ids = list(payload.get("manifest_item_ids") or ["ULD-1"])
        return LoadIQOutput(
            placements=[
                ULDPlacement(cargo_item_id=mid, uld_position="POS-A")
                for mid in manifest_ids
            ],
            weight_balance_ok=True,
            hazmat_conflicts=[],
            crew_instructions="Load per revised plan",
            ground_crew_notify_requested=not bool(payload.get("zone2_open")),
            manifest_item_ids_in=manifest_ids,
        )

    async def cargocomply(inp: dict[str, Any]) -> CargoComplyOutput:
        payload = dict(inp.get("payload") or {})
        payload["shipper_doc_excerpt"] = _sanitize(
            str(payload.get("shipper_doc_excerpt", "")), "shipper_doc"
        )
        chunk = payload.get("expected_chunk_id") or "CBP_2024_DG_Sec4"
        grounded = bool(payload.get("rag_has_coverage", True))
        if grounded:
            stm = [
                ComplianceStatement(
                    text="DG labeling required for Class 9.", source_chunk_id=chunk
                )
            ]
        else:
            stm = [
                ComplianceStatement(
                    text="Lane appears permissible.", source_chunk_id=None
                )
            ]
        return CargoComplyOutput(
            status="pass" if grounded else "hold",
            statements=stm,
            missing_docs=[],
            dg_accepted=bool(payload.get("dg_lane_ok", True)),
            escalation_required=not grounded,
        )

    return AgentRunners(
        clearpath=clearpath, loadiq=loadiq, cargocomply=cargocomply
    )
