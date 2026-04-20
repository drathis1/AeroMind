from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aeromind.schemas.domain import EventType, OrchestratorEvent


@dataclass
class IngestionResult:
    emitted: bool
    event: OrchestratorEvent | None


async def persist_event(session: AsyncSession, event: OrchestratorEvent) -> None:
    await session.execute(
        text(
            """
            INSERT INTO orchestrator_events (event_id, event_type, payload)
            VALUES (:event_id, :event_type, CAST(:payload AS JSONB))
            ON CONFLICT (event_id) DO NOTHING
            """
        ),
        {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "payload": json.dumps(event.payload),
        },
    )
    await session.commit()


def normalize_and_maybe_emit(
    *,
    event_type: EventType,
    raw: dict[str, Any],
    threshold_fn: Callable[[dict[str, Any]], bool] | None = None,
) -> IngestionResult:
    """Pure normalization; threshold_fn(raw)->bool decides emit."""
    should = threshold_fn is None or bool(threshold_fn(raw))
    if not should:
        return IngestionResult(False, None)
    ev = OrchestratorEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        payload=raw,
    )
    return IngestionResult(True, ev)
