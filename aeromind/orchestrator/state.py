from __future__ import annotations

from typing import Any, TypedDict


class OrchState(TypedDict, total=False):
    workflow_id: str
    event_id: str
    event_type: str
    payload: dict[str, Any]

    pending: list[str]
    completed: list[str]
    agent_results: dict[str, Any]

    reroute_complete: bool
    dg_accepted: bool
    cargo_is_dg_bool: bool
    reroute_new_country: bool
    open_human_gate: bool
    blast_radius_halt: bool
    status: str
    autonomous_commits: int
    messages: list[str]
