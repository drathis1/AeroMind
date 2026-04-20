from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.config import settings
from aeromind.llm.gemini_client import GeminiClient
from aeromind.schemas.agent_io import ClearPathOutput, ComplianceStatement, LoadIQOutput


@dataclass
class JudgeResult:
    payload: dict[str, Any]
    mandatory_human_review: bool


def _ungrounded(stmts: list[ComplianceStatement]) -> bool:
    for s in stmts:
        if s.text and not s.source_chunk_id:
            return True
    return False


def _pareto_dominated(selected: str | None, options: list[Any]) -> bool:
    if not selected or len(options) < 2:
        return False
    chosen = next((o for o in options if o.route_id == selected), None)
    if not chosen:
        return False
    for o in options:
        if o.route_id == selected:
            continue
        if (
            o.transit_delta_hours <= chosen.transit_delta_hours
            and o.cost_delta_usd <= chosen.cost_delta_usd
            and o.reliability_score >= chosen.reliability_score
        ) and (
            o.transit_delta_hours < chosen.transit_delta_hours
            or o.cost_delta_usd < chosen.cost_delta_usd
            or o.reliability_score > chosen.reliability_score
        ):
            return True
    return False


def _load_coverage_fail(manifest_ids: list[str], out: LoadIQOutput) -> bool:
    placed = {p.cargo_item_id for p in out.placements}
    return any(mid not in placed for mid in manifest_ids)


async def run_judge_for_workflow(
    *,
    session: AsyncSession | None,
    workflow_id: str,
    trace: dict[str, Any],
    agent_results: dict[str, Any],
) -> JudgeResult:
    flags: dict[str, Any] = {}
    mandatory = False

    cc = agent_results.get("CARGOCOMPLY")
    if cc is not None and hasattr(cc, "statements"):
        if _ungrounded(list(cc.statements)):
            flags["ungrounded_compliance"] = True
            mandatory = True
    elif isinstance(cc, dict) and cc.get("statements"):
        stmts = [ComplianceStatement.model_validate(s) for s in cc["statements"]]
        if _ungrounded(stmts):
            flags["ungrounded_compliance"] = True
            mandatory = True

    cp = agent_results.get("CLEARPATH")
    if isinstance(cp, ClearPathOutput):
        opts = list(cp.ranked_options or cp.ground_truth_ranked_for_judge or [])
        if _pareto_dominated(cp.selected_option_id, opts):
            flags["route_selection_anomaly"] = True
    elif isinstance(cp, dict):
        from aeromind.schemas.agent_io import RerouteOption

        opts = [RerouteOption.model_validate(x) for x in (cp.get("ranked_options") or [])]
        if _pareto_dominated(cp.get("selected_option_id"), opts):
            flags["route_selection_anomaly"] = True

    lq = agent_results.get("LOADIQ")
    manifest_ids = []
    if isinstance(trace.get("payload"), dict):
        manifest_ids = list(trace["payload"].get("manifest_item_ids") or [])
    if isinstance(lq, LoadIQOutput):
        if manifest_ids and _load_coverage_fail(manifest_ids, lq):
            flags["load_plan_coverage_fail"] = True
            mandatory = True

    llm = GeminiClient(model=settings.gemini_model_judge)
    if llm.enabled():
        judge_prompt = {
            "instruction": "Summarize evaluation flags only; return JSON {summary, reasoning_faithfulness_score}.",
            "flags": flags,
            "workflow_id": workflow_id,
        }
        extra = await llm.generate_json_loose(
            "You are an LLM-as-judge with no tool access.",
            json.dumps(judge_prompt),
        )
        flags["judge_model_notes"] = extra

    if session is not None:
        await session.execute(
            text(
                """
                INSERT INTO llm_judge_evaluations (workflow_id, payload, mandatory_human_review)
                VALUES (:wf, CAST(:payload AS JSONB), :mhr)
                """
            ),
            {"wf": workflow_id, "payload": json.dumps(flags), "mhr": mandatory},
        )
        await session.commit()

    return JudgeResult(payload=flags, mandatory_human_review=mandatory)


def judge_heuristic_only(
    agent_results: dict[str, Any],
) -> JudgeResult:
    """For tests without DB/LLM."""
    return JudgeResult(payload={"synthetic": True}, mandatory_human_review=False)
