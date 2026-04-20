from aeromind.audit.chain import hash_entry, verify_chain


def test_hash_chain_verifies():
    h0 = hash_entry(
        actor="ORCHESTRATOR",
        decision_payload={"a": 1},
        evidence_refs=[],
        outcome="WORKFLOW_CLOSED_CLEAN",
        prev_hash=None,
    )
    h1 = hash_entry(
        actor="LOADIQ",
        decision_payload={"b": 2},
        evidence_refs=["x"],
        outcome="ESCALATION_FIRED",
        prev_hash=h0,
    )
    rows = [
        {"id": 1, "actor": "ORCHESTRATOR", "decision_payload": {"a": 1}, "evidence_refs": [], "outcome": "WORKFLOW_CLOSED_CLEAN", "prev_hash": None, "entry_hash": h0},
        {"id": 2, "actor": "LOADIQ", "decision_payload": {"b": 2}, "evidence_refs": ["x"], "outcome": "ESCALATION_FIRED", "prev_hash": h0, "entry_hash": h1},
    ]
    ok, err = verify_chain(rows)
    assert ok and err is None


def test_tamper_detected():
    h0 = hash_entry(
        actor="X", decision_payload={}, evidence_refs=[], outcome="A", prev_hash=None
    )
    rows = [
        {"id": 1, "actor": "X", "decision_payload": {}, "evidence_refs": [], "outcome": "A", "prev_hash": None, "entry_hash": "tampered"},
    ]
    ok, err = verify_chain(rows)
    assert not ok
