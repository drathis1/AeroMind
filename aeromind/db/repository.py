from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.audit.chain import hash_entry


class AuditRepository:
    @staticmethod
    async def append_entry(
        session: AsyncSession,
        *,
        workflow_id: str | None,
        actor: str,
        decision_payload: dict[str, Any],
        evidence_refs: list[str],
        outcome: str,
    ) -> str:
        if workflow_id is None:
            res = await session.execute(
                text(
                    """
                    SELECT entry_hash FROM audit_log
                    WHERE workflow_id IS NULL
                    ORDER BY id DESC LIMIT 1
                    """
                )
            )
        else:
            res = await session.execute(
                text(
                    """
                    SELECT entry_hash FROM audit_log
                    WHERE workflow_id = :wf
                    ORDER BY id DESC LIMIT 1
                    """
                ),
                {"wf": workflow_id},
            )
        row = res.first()
        prev_hash = row[0] if row else None

        entry_hash = hash_entry(
            actor=actor,
            decision_payload=decision_payload,
            evidence_refs=evidence_refs,
            outcome=outcome,
            prev_hash=prev_hash,
        )
        await session.execute(
            text(
                """
                INSERT INTO audit_log (workflow_id, actor, decision_payload, evidence_refs, outcome, prev_hash, entry_hash)
                VALUES (:workflow_id, :actor, CAST(:decision_payload AS JSONB), CAST(:evidence_refs AS JSONB), :outcome, :prev_hash, :entry_hash)
                """
            ),
            {
                "workflow_id": workflow_id,
                "actor": actor,
                "decision_payload": json.dumps(decision_payload),
                "evidence_refs": json.dumps(evidence_refs),
                "outcome": outcome,
                "prev_hash": prev_hash,
                "entry_hash": entry_hash,
            },
        )
        await session.commit()
        return entry_hash
