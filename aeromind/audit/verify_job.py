"""Nightly-style audit chain verification (skeleton)."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.audit.chain import verify_chain


async def verify_audit_chain_for_workflow(session: AsyncSession, workflow_id: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT id, actor, decision_payload, evidence_refs, outcome, prev_hash, entry_hash
            FROM audit_log
            WHERE workflow_id = :wf
            ORDER BY id ASC
            """
        ),
        {"wf": workflow_id},
    )
    rows_raw = result.mappings().all()
    rows: list[dict] = []
    for r in rows_raw:
        d = dict(r)
        if isinstance(d.get("evidence_refs"), str):
            d["evidence_refs"] = json.loads(d["evidence_refs"])
        rows.append(d)
    ok, _ = verify_chain(rows)
    return ok
