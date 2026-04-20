from __future__ import annotations

import re
from dataclasses import dataclass

BLOCKLIST = (
    r"ignore\s+(all\s+)?(prior\s+)?instructions",
    r"system\s*:\s*",
    r"you\s+are\s+now",
    r"disregard\s+the\s+above",
    r"<\s*script",
)


@dataclass
class InjectionReport:
    flagged: bool
    redacted_text: str
    pattern: str | None = None


def sanitize_external_text(text: str, *, source: str) -> InjectionReport:
    """Two-pass: regex blocklist + crude structural check (very long unbroken tokens)."""
    t = text or ""
    for pat in BLOCKLIST:
        if re.search(pat, t, re.I):
            return InjectionReport(True, "[REDACTED_INJECTION]", pat)
    if len(t) > 8000:
        return InjectionReport(True, t[:8000] + "…", "length_cap")
    tokens = t.split()
    if any(len(tok) > 120 for tok in tokens):
        return InjectionReport(True, "[REDACTED_ANOMALOUS_TOKEN]", "token_length")
    return InjectionReport(False, t, None)
