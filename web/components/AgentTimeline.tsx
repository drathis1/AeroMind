"use client";

import { CheckCircle2, Clock, Loader2, ShieldAlert, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { agentLabel } from "@/lib/format";
import { formatTime } from "@/lib/utils";
import { AgentIconDot } from "./AgentPill";
import { ConfidenceChip, type ConfidenceLevel } from "./ConfidenceChip";
import type { OrderDetail, TimelineStep } from "@/lib/types";

/**
 * Translate the backend's agent-specific result into plain-English reasoning
 * lines plus optional confidence. No jargon codes in the UI.
 */
function readReasoning(agentKey: string, result: any): {
  summary: string;
  reasoning: string[];
  confidence: { level: ConfidenceLevel; note: string } | null;
} {
  if (!result) return { summary: "Waiting to run.", reasoning: [], confidence: null };
  const key = agentKey.toUpperCase();

  if (key === "CARGOCOMPLY") {
    const status = result.status;
    const statements = Array.isArray(result.statements) ? result.statements : [];
    const missing = Array.isArray(result.missing_docs) ? result.missing_docs : [];
    if (status === "hold") {
      return {
        summary: "Flagged compliance hold — documentation missing for the declared lane.",
        reasoning: [
          ...statements.map((s: any) => s?.text).filter(Boolean),
          missing.length
            ? `Missing documents: ${missing.join(", ")}.`
            : "",
        ].filter(Boolean),
        confidence: {
          level: "high",
          note: `${statements.length || 1} regulatory reference${statements.length === 1 ? "" : "s"} matched`,
        },
      };
    }
    return {
      summary: "Cleared compliance — documents and DG classification acceptable.",
      reasoning: statements.map((s: any) => s?.text).filter(Boolean),
      confidence: {
        level: "high",
        note: `${statements.length || 1} regulatory reference${statements.length === 1 ? "" : "s"} matched`,
      },
    };
  }

  if (key === "CLEARPATH") {
    const opts = Array.isArray(result.ranked_options) ? result.ranked_options : [];
    const selected = result.selected_option_id;
    const sel = opts.find((o: any) => o?.route_id === selected);
    if (result.escalation_required) {
      return {
        summary: result.disruption_summary || "Route constraints violated — escalation required.",
        reasoning: [
          result.escalation_reason || "Cross-border or delay constraint breach.",
          "No reroute option satisfied the active constraints; paused for human review.",
        ],
        confidence: { level: "low", note: "no option met constraints" },
      };
    }
    return {
      summary: result.disruption_summary || "Optimal route selected.",
      reasoning: [
        `Evaluated ${opts.length} route option${opts.length === 1 ? "" : "s"}; selected ${selected || "primary"}.`,
        sel
          ? `Primary metrics — reliability ${(Number(sel.reliability_score) * 100).toFixed(0)}%, +${sel.transit_delta_hours}h transit, cost delta ${sel.cost_delta_usd === 0 ? "±0" : "$" + sel.cost_delta_usd}.`
          : "",
      ].filter(Boolean),
      confidence: sel
        ? {
            level: sel.reliability_score >= 0.9 ? "high" : sel.reliability_score >= 0.8 ? "medium" : "low",
            note: `reliability ${(Number(sel.reliability_score) * 100).toFixed(0)}%`,
          }
        : null,
    };
  }

  if (key === "LOADIQ") {
    const placements = Array.isArray(result.placements) ? result.placements : [];
    const conflicts = Array.isArray(result.hazmat_conflicts) ? result.hazmat_conflicts : [];
    if (result.escalation_required) {
      return {
        summary: "Load plan could not be finalized — human review required.",
        reasoning: [
          result.escalation_reason || "Weight-balance or hazmat conflict.",
          conflicts.length ? `Hazmat conflicts: ${conflicts.join("; ")}.` : "",
        ].filter(Boolean),
        confidence: { level: "low", note: "constraints unresolved" },
      };
    }
    return {
      summary: "Weight-balance and hazmat checks passed; ground crew notified.",
      reasoning: [
        `Placed ${placements.length} ULD${placements.length === 1 ? "" : "s"}.`,
        result.crew_instructions || "",
      ].filter(Boolean),
      confidence: { level: "high", note: "no conflicts detected" },
    };
  }

  return {
    summary: "Agent completed.",
    reasoning: [],
    confidence: null,
  };
}

function stepIcon(status: TimelineStep["status"]) {
  switch (status) {
    case "done":
      return { icon: <CheckCircle2 className="h-4 w-4" />, ring: "ring-emerald-400/30", bg: "bg-emerald-500/10", text: "text-emerald-300" };
    case "running":
      return { icon: <Loader2 className="h-4 w-4 animate-spin" />, ring: "ring-sky-400/30", bg: "bg-sky-500/10", text: "text-sky-300" };
    case "failed":
      return { icon: <ShieldAlert className="h-4 w-4" />, ring: "ring-amber-400/30", bg: "bg-amber-500/10", text: "text-amber-200" };
    default:
      return { icon: <Clock className="h-4 w-4" />, ring: "ring-slate-700", bg: "bg-slate-800/60", text: "text-slate-400" };
  }
}

export function AgentTimeline({ order }: { order: OrderDetail }) {
  const steps = order.timeline;
  const logs = order.agent_logs || {};
  const results = order.agent_results || {};

  return (
    <ol className="relative flex flex-col">
      {steps.map((step, idx) => {
        const s = stepIcon(step.status);
        const agentKey = agentKeyFor(step);
        const agentLogs = agentKey ? logs[agentKey] || [] : [];
        const lastLog = agentLogs[agentLogs.length - 1];
        const ts = extractTs(lastLog);
        const msg = stripTs(lastLog);
        const reasoning = agentKey ? readReasoning(agentKey, results[agentKey]) : null;
        const isEscalated = step.status === "failed";
        const isRunning = step.status === "running";

        return (
          <li key={step.id} className="relative pl-12 pb-6 last:pb-0">
            {idx < steps.length - 1 ? (
              <span
                aria-hidden
                className={cn(
                  "absolute left-[15px] top-8 bottom-0 w-px",
                  step.status === "done" ? "bg-slate-700" : "bg-slate-800",
                )}
              />
            ) : null}

            <span
              className={cn(
                "absolute left-0 top-1 inline-flex h-8 w-8 items-center justify-center rounded-full ring-1",
                s.ring,
                s.bg,
                s.text,
              )}
            >
              {s.icon}
            </span>

            <div
              className={cn(
                "rounded-lg border px-4 py-3",
                isEscalated
                  ? "border-amber-400/40 bg-amber-500/5"
                  : isRunning
                    ? "border-sky-400/30 bg-sky-500/5"
                    : "border-slate-800 bg-slate-900/40",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-slate-100">{step.label}</span>
                    {step.agent ? <AgentIconDot agent={step.agent} /> : null}
                    {step.agent ? (
                      <span className="text-xs text-slate-400">{agentLabel(step.agent)}</span>
                    ) : (
                      <span className="text-xs text-slate-500">{step.lane}</span>
                    )}
                    {step.status === "done" && !isEscalated ? (
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-800/70 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-slate-400 ring-1 ring-slate-700">
                        <Sparkles className="h-3 w-3" /> AI decided
                      </span>
                    ) : null}
                    {isEscalated ? (
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-amber-200 ring-1 ring-amber-400/30">
                        <ShieldAlert className="h-3 w-3" /> Waiting for human
                      </span>
                    ) : null}
                  </div>
                </div>
                <span className="shrink-0 text-[11px] text-slate-500 whitespace-nowrap">
                  {ts ? formatTime(ts) : statusLabel(step.status)}
                </span>
              </div>

              {reasoning && step.status !== "pending" ? (
                <div className="mt-2 text-sm text-slate-300">
                  {reasoning.summary}
                </div>
              ) : null}

              {reasoning && reasoning.reasoning.length > 0 && step.status !== "pending" ? (
                <ul className="mt-2 space-y-1">
                  {reasoning.reasoning.map((line, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-xs text-slate-400 leading-relaxed"
                    >
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-slate-600" />
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              ) : null}

              {reasoning?.confidence && step.status === "done" ? (
                <div className="mt-2">
                  <ConfidenceChip level={reasoning.confidence.level} note={reasoning.confidence.note} />
                </div>
              ) : null}

              {isRunning && msg ? (
                <div className="mt-2 text-xs text-sky-200/80 italic">
                  {msg}
                </div>
              ) : null}

              {step.status === "pending" ? (
                <div className="mt-1 text-xs text-slate-500">
                  Not started yet.
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function agentKeyFor(step: TimelineStep): string | null {
  if (!step.agent) return null;
  const v = step.agent.toUpperCase();
  if (v.includes("COMPLY")) return "CARGOCOMPLY";
  if (v.includes("CLEAR")) return "CLEARPATH";
  if (v.includes("LOAD")) return "LOADIQ";
  return null;
}

function extractTs(line?: string): string | null {
  if (!line) return null;
  const m = line.match(/^\[([^\]]+)\]/);
  return m ? m[1] : null;
}
function stripTs(line?: string): string {
  if (!line) return "";
  return line.replace(/^\[[^\]]+\]\s*/, "");
}
function statusLabel(s: TimelineStep["status"]): string {
  if (s === "pending") return "Queued";
  if (s === "running") return "Running now";
  if (s === "done") return "Completed";
  return "Paused";
}
