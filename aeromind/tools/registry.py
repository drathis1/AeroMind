from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.schemas.domain import AgentId


@dataclass
class ToolContext:
    workflow_id: str
    agent_id: AgentId
    session: AsyncSession | None
    open_zone2_or_zone3: bool
    dg_accepted: bool
    cargo_is_dg: bool
    reroute_to_new_country: bool
    autonomous_commits: int
    blast_radius_cap: int


ALLOWLIST: dict[AgentId, frozenset[str]] = {
    AgentId.LOADIQ: frozenset(
        {
            "aircraft_db_lookup",
            "weight_balance_check",
            "hazmat_rules_lookup",
            "booking_load_status_update",
            "ground_crew_notify",
        }
    ),
    AgentId.CLEARPATH: frozenset(
        {
            "weather_fetch",
            "notam_fetch",
            "booking_read",
            "booking_write",
            "route_optimize",
            "shipper_notify",
        }
    ),
    AgentId.CARGOCOMPLY: frozenset(
        {
            "rag_search",
            "sanctions_check",
            "document_template_fill",
            "shipper_request_docs",
        }
    ),
}


async def log_violation(
    session: AsyncSession | None,
    *,
    workflow_id: str,
    agent_id: AgentId,
    tool_name: str,
    detail: dict[str, Any],
) -> None:
    if session is None:
        return
    await session.execute(
        text(
            """
            INSERT INTO governance_violations (workflow_id, agent_id, tool_name, detail)
            VALUES (:workflow_id, :agent_id, :tool_name, CAST(:detail AS JSONB))
            """
        ),
        {
            "workflow_id": workflow_id,
            "agent_id": agent_id.value,
            "tool_name": tool_name,
            "detail": json.dumps(detail),
        },
    )
    await session.commit()


def enforce_allowlist(ctx: ToolContext, tool_name: str) -> tuple[bool, str | None]:
    allowed = ALLOWLIST.get(ctx.agent_id, frozenset())
    if tool_name not in allowed:
        return False, "TOOL_NOT_IN_ALLOWLIST"
    if tool_name == "ground_crew_notify" and ctx.open_zone2_or_zone3:
        return False, "CREW_NOTIFY_WRITE_LOCK"
    if (
        tool_name == "booking_write"
        and ctx.agent_id == AgentId.CLEARPATH
        and ctx.cargo_is_dg
        and ctx.reroute_to_new_country
        and not ctx.dg_accepted
    ):
        return False, "DG_LOCK_BREACH"
    if tool_name == "booking_write" and ctx.agent_id == AgentId.CARGOCOMPLY:
        return False, "CARGOCOMPLY_BOOKING_FORBIDDEN"
    if ctx.autonomous_commits >= ctx.blast_radius_cap and tool_name in ("booking_write", "ground_crew_notify"):
        return False, "BLAST_RADIUS_PENDING"
    return True, None


class ToolRegistry:
    """Maps tool names to callables; wraps with allowlist enforcement."""

    def __init__(self) -> None:
        self._fns: dict[str, Callable[..., Awaitable[Any] | Any]] = {}

    def register(self, name: str, fn: Callable[..., Awaitable[Any] | Any]) -> None:
        self._fns[name] = fn

    async def call(
        self,
        name: str,
        ctx: ToolContext,
        *,
        args: dict[str, Any],
    ) -> Any:
        ok, reason = enforce_allowlist(ctx, name)
        if not ok:
            await log_violation(
                ctx.session,
                workflow_id=ctx.workflow_id,
                agent_id=ctx.agent_id,
                tool_name=name,
                detail={"reason": reason, "args": args},
            )
            raise PermissionError(reason or "blocked")
        fn = self._fns.get(name)
        if not fn:
            raise KeyError(f"unknown tool {name}")
        out = fn(**args)
        if hasattr(out, "__await__"):
            return await out
        return out
