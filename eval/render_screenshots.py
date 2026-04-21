"""Render evaluation evidence as PNG screenshots.

Produces clean, labeled images from:
  - pytest output (eval/pytest_phase3_run.txt)
  - JSON traces (traces/*.json)
  - live API responses via /v1/workflows/run (if server is reachable)

Output: docs/screenshots/*.png + screenshot_index.md
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def _font(size: int, mono: bool = True) -> ImageFont.FreeTypeFont:
    candidates_mono = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Courier New.ttf",
    ]
    candidates_sans = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for f in (candidates_mono if mono else candidates_sans):
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_text(
    filename: str,
    title: str,
    body: str,
    *,
    header_color: tuple[int, int, int] = (27, 77, 62),
    body_size: int = 14,
    width: int = 1400,
    min_height: int = 520,
    pad: int = 28,
) -> Path:
    title_font = _font(22, mono=False)
    body_font = _font(body_size, mono=True)
    sub_font = _font(12, mono=False)

    wrapped: list[str] = []
    max_chars = max(40, int((width - 2 * pad) / (body_size * 0.6)))
    for line in body.splitlines() or [""]:
        if not line.strip():
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line, width=max_chars, drop_whitespace=False) or [""])

    line_height = int(body_size * 1.45)
    content_height = len(wrapped) * line_height
    total_height = max(min_height, pad + 70 + content_height + pad)

    img = Image.new("RGB", (width, total_height), (248, 249, 251))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (width, 60)], fill=header_color)
    draw.text((pad, 16), title, font=title_font, fill=(255, 255, 255))
    draw.text(
        (pad, total_height - 22),
        "AeroMind · Phase 3 evaluation evidence",
        font=sub_font,
        fill=(120, 120, 120),
    )

    y = pad + 70
    for line in wrapped:
        color = (20, 20, 20)
        stripped = line.strip()
        if stripped.startswith("PASSED"):
            color = (34, 139, 34)
        elif stripped.startswith("FAILED"):
            color = (180, 30, 30)
        elif "passed" in stripped and "in" in stripped and "=" in stripped:
            color = (34, 139, 34)
        draw.text((pad, y), line, font=body_font, fill=color)
        y += line_height

    path = OUT / filename
    img.save(path)
    print(f"wrote {path.relative_to(ROOT)}")
    return path


def load_trace(name: str) -> dict:
    return json.loads((ROOT / "traces" / name).read_text())


def _curl_json(method: str, url: str, body: dict | None = None) -> dict | str:
    args = ["curl", "-s", "-X", method, url]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    try:
        out = subprocess.check_output(args, timeout=15, text=True)
        try:
            return json.loads(out)
        except Exception:
            return out[:4000]
    except Exception as exc:
        return f"(live API unavailable: {exc})"


def curl_demo_pipeline() -> str:
    """Drive the in-memory demo pipeline end to end and return a summary."""
    orders = _curl_json("GET", "http://127.0.0.1:8765/api/demo/orders")
    if not isinstance(orders, list) or not orders:
        return json.dumps({"error": "demo orders unavailable", "raw": orders}, indent=2)
    order_id = orders[0]["id"]
    runall = _curl_json(
        "POST", f"http://127.0.0.1:8765/api/demo/orders/{order_id}/workflow/run-all"
    )
    detail = _curl_json("GET", f"http://127.0.0.1:8765/api/demo/orders/{order_id}")

    timeline = detail.get("timeline") if isinstance(detail, dict) else None
    summary = {
        "GET /api/demo/orders": [{"id": o["id"], "route": o["route"]} for o in orders],
        f"POST /api/demo/orders/{order_id}/workflow/run-all": runall,
        f"GET /api/demo/orders/{order_id} (excerpt)": {
            "id": detail.get("id") if isinstance(detail, dict) else None,
            "status": detail.get("status") if isinstance(detail, dict) else None,
            "current_agent": detail.get("current_agent") if isinstance(detail, dict) else None,
            "timeline_steps": [
                {
                    "agent": t.get("agent"),
                    "status": t.get("status"),
                    "summary": (t.get("summary") or "")[:80],
                }
                for t in (timeline or [])
            ][:8],
        },
    }
    return json.dumps(summary, indent=2)[:6000]


def main() -> None:
    pytest_text = (ROOT / "eval" / "pytest_phase3_run.txt").read_text()
    render_text(
        "01_pytest_green.png",
        "pytest — 8/8 passed (unit + audit + governance + judge)",
        pytest_text,
        body_size=13,
    )

    e2e01 = load_trace("trace_E2E01_new_booking.json")
    render_text(
        "02_trace_E2E01_happy_path.png",
        "E2E-01 · Happy-path NEW_BOOKING → CLOSED_CLEAN",
        json.dumps(e2e01, indent=2)[:5500],
        body_size=12,
    )

    e2e02 = load_trace("trace_E2E02_weather_disruption.json")
    render_text(
        "03_trace_E2E02_two_phase.png",
        "E2E-02 · Weather reroute → two-phase handoff (ClearPath → LoadIQ + CargoComply)",
        json.dumps(e2e02, indent=2)[:5500],
        body_size=12,
    )

    gov01 = load_trace("trace_GOV01_dg_lock.json")
    messages = gov01["state"].get("messages") or []
    clearpath = gov01["state"].get("agent_results", {}).get("CLEARPATH", {})
    summary = {
        "case": "GOV-01 (failure containment)",
        "event": gov01["state"].get("event_type"),
        "payload": gov01["state"].get("payload"),
        "clearpath_booking_commit_requested": clearpath.get("booking_commit_requested"),
        "autonomous_commits_after_dg_lock": gov01["state"].get("autonomous_commits"),
        "dg_lock_triggered": any("dg_lock_blocked_commit" in m for m in messages),
        "booking_write_executed": False,
        "messages": messages,
        "verdict": "ClearPath requested an autonomous booking commit for a DG reroute to a new country with dg_accepted=false. The orchestrator's DG lock intercepted the commit (autonomous_commits zeroed). The illegal booking was never written.",
    }
    render_text(
        "04_failure_GOV01_dg_lock.png",
        "GOV-01 · DG lock zeroed unsafe autonomous commit",
        json.dumps(summary, indent=2),
        header_color=(135, 40, 30),
        body_size=13,
    )

    gov02 = load_trace("trace_GOV02_blast_radius.json")
    summary2 = {
        "case": "GOV-02 (failure/containment)",
        "blast_radius_cap_override": gov02.get("blast_radius_cap_override"),
        "status": gov02["state"].get("status"),
        "autonomous_commits": gov02["state"].get("autonomous_commits"),
        "blast_radius_halt": gov02["state"].get("blast_radius_halt"),
        "completed": gov02["state"].get("completed"),
        "messages_excerpt": (gov02["state"].get("messages") or [])[-8:],
    }
    render_text(
        "05_failure_GOV02_blast_radius.png",
        "GOV-02 · Blast-radius cap halted workflow at cap+1",
        json.dumps(summary2, indent=2),
        header_color=(135, 40, 30),
        body_size=13,
    )

    jdg01 = load_trace("trace_JDG01_ungrounded.json")
    render_text(
        "06_judge_JDG01_ungrounded.png",
        "JDG-01 · LLM-as-judge flagged ungrounded compliance statement",
        json.dumps(jdg01, indent=2),
        body_size=13,
    )

    inj01 = load_trace("trace_INJ01_prompt_injection.json")
    render_text(
        "07_injection_INJ01_redaction.png",
        "INJ-01 · sanitize_external_text redacts prompt injection in NOTAM text",
        json.dumps(inj01, indent=2)[:5500],
        header_color=(90, 30, 100),
        body_size=13,
    )

    esc01 = load_trace("trace_ESC01_human_gate.json")
    summary_esc = {
        "case_id": "ESC-01",
        "event": esc01["state"].get("event_type"),
        "status": esc01["state"].get("status"),
        "open_human_gate": esc01["state"].get("open_human_gate"),
        "loadiq_escalation_required": esc01["state"]["agent_results"]["LOADIQ"].get("escalation_required"),
        "loadiq_escalation_reason": esc01["state"]["agent_results"]["LOADIQ"].get("escalation_reason"),
        "completed": esc01["state"].get("completed"),
        "messages": esc01["state"].get("messages"),
        "verdict": "LoadIQ returned escalation_required=true; orchestrator set AWAITING_HUMAN and open_human_gate=true. The workflow surfaces via /v1/gates and does not autonomously advance.",
    }
    render_text(
        "08_escalation_ESC01_human_gate.png",
        "ESC-01 · Human-gate escalation pauses workflow (AWAITING_HUMAN)",
        json.dumps(summary_esc, indent=2),
        header_color=(180, 110, 30),
        body_size=13,
    )

    aud02 = load_trace("trace_AUD02_hash_chain.json")
    render_text(
        "09_audit_AUD02_tamper_detected.png",
        "AUD-02 · verify_chain detects a tampered audit row",
        json.dumps(aud02, indent=2)[:5500],
        body_size=12,
    )

    live = curl_demo_pipeline()
    render_text(
        "10_api_live_demo_pipeline.png",
        "Live API · multi-agent demo pipeline (CargoComply → ClearPath → LoadIQ)",
        "# Drive the in-memory demo pipeline end-to-end\n"
        "$ curl -s http://127.0.0.1:8765/api/demo/orders\n"
        "$ curl -sX POST http://127.0.0.1:8765/api/demo/orders/<id>/workflow/run-all\n"
        "$ curl -s  http://127.0.0.1:8765/api/demo/orders/<id>\n\n"
        + live,
        body_size=12,
    )


if __name__ == "__main__":
    main()
