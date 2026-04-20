from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def hash_entry(
    *,
    actor: str,
    decision_payload: dict[str, Any],
    evidence_refs: list[str],
    outcome: str,
    prev_hash: str | None,
) -> str:
    payload = _canonical_json(
        {
            "actor": actor,
            "decision_payload": decision_payload,
            "evidence_refs": evidence_refs,
            "outcome": outcome,
            "prev_hash": prev_hash or "",
        }
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_chain(rows: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """rows: ordered audit rows with keys prev_hash, entry_hash, actor, decision_payload, evidence_refs, outcome."""
    prev: str | None = None
    for row in rows:
        expected = hash_entry(
            actor=row["actor"],
            decision_payload=row["decision_payload"] if isinstance(row["decision_payload"], dict) else {},
            evidence_refs=list(row.get("evidence_refs") or []),
            outcome=str(row["outcome"]),
            prev_hash=prev,
        )
        if expected != row.get("entry_hash"):
            return False, f"broken at id={row.get('id')}"
        prev = row["entry_hash"]
    return True, None
