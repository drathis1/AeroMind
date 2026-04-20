from __future__ import annotations

from typing import Any

from aeromind.agents.runner import AgentRunners
from aeromind.injection.filter import sanitize_external_text
from aeromind.llm.gemini_client import GeminiClient
from aeromind.schemas.agent_io import (
    CargoComplyOutput,
    ClearPathOutput,
    ComplianceStatement,
    LoadIQOutput,
    RerouteOption,
    ULDPlacement,
)


def build_default_runners(*, llm: GeminiClient | None = None) -> AgentRunners:
    client = llm or GeminiClient()

    async def clearpath(inp: dict[str, Any]) -> ClearPathOutput:
        payload = dict(inp.get("payload") or {})
        raw_notam = str(payload.get("notam_text", ""))
        rep = sanitize_external_text(raw_notam, source="notam")
        payload["notam_text"] = rep.redacted_text
        if client.enabled():
            sys = (
                "You are ClearPath, an airline cargo disruption agent. "
                "Return strict JSON matching the schema. "
                "If reroute is confirmed, set handoff.reroute_complete true and include ranked reroute options."
            )
            user = f"Context: {payload}"
            return await client.generate_json(sys, user, ClearPathOutput)
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
            disruption_summary="NOTAM affecting corridor" if payload.get("bulk_notam") else "Weather caution",
            ranked_options=options,
            ground_truth_ranked_for_judge=list(options),
            selected_option_id="r1",
            booking_commit_requested=bool(payload.get("autonomous_booking_ok", True)),
            shipper_notified=False,
            handoff={"reroute_complete": True, "new_country": bool(payload.get("reroute_new_country", False))},
            escalation_required=bool(payload.get("force_escalation", False)),
        )

    async def loadiq(inp: dict[str, Any]) -> LoadIQOutput:
        payload = dict(inp.get("payload") or {})
        raw_manifest = str(payload.get("manifest_notes", ""))
        rep = sanitize_external_text(raw_manifest, source="manifest")
        payload["manifest_notes"] = rep.redacted_text
        manifest_ids = list(payload.get("manifest_item_ids") or ["ULD-1"])
        if client.enabled():
            sys = (
                "You are LoadIQ, cargo load optimization agent. "
                "Return JSON: placements for every manifest id, weight_balance_ok bool, hazmat_conflicts list."
            )
            return await client.generate_json(sys, f"Context: {payload}", LoadIQOutput)
        return LoadIQOutput(
            placements=[ULDPlacement(cargo_item_id=mid, uld_position="POS-A") for mid in manifest_ids],
            weight_balance_ok=True,
            hazmat_conflicts=[],
            crew_instructions="Load per revised plan",
            ground_crew_notify_requested=not bool(payload.get("zone2_open")),
            manifest_item_ids_in=manifest_ids,
        )

    async def cargocomply(inp: dict[str, Any]) -> CargoComplyOutput:
        payload = dict(inp.get("payload") or {})
        doc = str(payload.get("shipper_doc_excerpt", ""))
        rep = sanitize_external_text(doc, source="shipper_doc")
        payload["shipper_doc_excerpt"] = rep.redacted_text
        if client.enabled():
            sys = (
                "You are CargoComply. Only cite regulations using source_chunk_id from provided context. "
                "Return JSON with statements list including source_chunk_id for each."
            )
            return await client.generate_json(sys, f"Context: {payload}", CargoComplyOutput)
        chunk = payload.get("expected_chunk_id") or "CBP_2024_DG_Sec4"
        grounded = bool(payload.get("rag_has_coverage", True))
        if grounded:
            stm = [ComplianceStatement(text="DG labeling required for Class 9.", source_chunk_id=chunk)]
        else:
            stm = [ComplianceStatement(text="Lane appears permissible.", source_chunk_id=None)]
        return CargoComplyOutput(
            status="pass" if grounded else "hold",
            statements=stm,
            missing_docs=[],
            dg_accepted=bool(payload.get("dg_lane_ok", True)),
            escalation_required=not grounded,
        )

    return AgentRunners(clearpath=clearpath, loadiq=loadiq, cargocomply=cargocomply)
