"use client";

import { useState } from "react";
import { Bell, CheckCircle2, MessageSquare, Pause, ShieldAlert, X } from "lucide-react";
import { Button } from "./ui/Button";
import { Modal } from "./ui/Modal";
import { cn } from "@/lib/utils";
import { agentLabel } from "@/lib/format";
import { api } from "@/lib/api";
import type { OrderDetail } from "@/lib/types";

interface Props {
  order: OrderDetail;
  onResolved?: () => void;
}

export function EscalationCard({ order, onResolved }: Props) {
  const e = order.escalation;
  const [pending, setPending] = useState<null | "approve" | "hold">(null);
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!e.active) return null;

  const headline = decisionHeadline(e.source_agent, e.message);
  const context = decisionContext(e.source_agent, e.message);

  const runApprove = async () => {
    setError(null);
    setPending("approve");
    try {
      await api.resolveEscalation(order.id, {
        action: "approve",
        note: note.trim() || null,
      });
      setSuccess("Approved — re-queuing the agent now. Dashboard will update on next poll.");
      setNote("");
      onResolved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(null);
    }
  };

  const runHold = async () => {
    if (note.trim().length < 3) {
      setNoteOpen(true);
      return;
    }
    setError(null);
    setPending("hold");
    try {
      await api.resolveEscalation(order.id, {
        action: "resolve",
        note: note.trim(),
      });
      setSuccess("Held for review. Workflow will pause until you revisit it.");
      setNote("");
      onResolved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(null);
    }
  };

  return (
    <>
      <div
        className={cn(
          "rounded-xl border border-amber-400/40 bg-amber-500/[0.06] px-5 py-4",
          "shadow-[0_0_0_1px_rgba(251,191,36,0.15)]",
          "animate-slide-up",
        )}
      >
        <div className="flex items-start gap-4">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-amber-500/20 ring-1 ring-amber-400/40 text-amber-200">
            <Bell className="h-4 w-4" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-amber-200/90">
              <ShieldAlert className="h-3.5 w-3.5" />
              Human decision required
            </div>
            <h2 className="mt-1 text-lg font-semibold text-slate-50">{headline}</h2>
            <p className="mt-1 text-sm text-slate-300 max-w-3xl">
              <span className="text-amber-200">{agentLabel(e.source_agent)}</span> flagged this —{" "}
              {context}
            </p>

            {success ? (
              <div className="mt-3 inline-flex items-center gap-2 rounded-md bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300 ring-1 ring-emerald-400/25">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {success}
              </div>
            ) : (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button variant="warning" onClick={runApprove} loading={pending === "approve"}>
                  <CheckCircle2 className="h-4 w-4" />
                  Approve &amp; continue
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setNoteOpen(true)}
                  loading={pending === "hold"}
                >
                  <Pause className="h-4 w-4" />
                  Hold for review
                </Button>
                <button
                  onClick={() => setNoteOpen(true)}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  Add a rationale note
                </button>
              </div>
            )}

            {error ? (
              <div className="mt-3 text-xs text-rose-300">{error}</div>
            ) : null}
          </div>
        </div>
      </div>

      <Modal
        open={noteOpen}
        onClose={() => setNoteOpen(false)}
        title="Add a rationale"
        description="Your note is attached to the audit trail and surfaced to whoever picks this up next."
        footer={
          <>
            <Button variant="ghost" onClick={() => setNoteOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setNoteOpen(false);
                void runHold();
              }}
              disabled={note.trim().length < 3}
            >
              Save &amp; hold
            </Button>
          </>
        }
      >
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={4}
          placeholder="Why is this being held? e.g. awaiting confirmation from shipper on customs paperwork."
          className="w-full rounded-md border border-slate-700 bg-slate-950/60 p-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-sky-400/60 focus:ring-1 focus:ring-sky-400/40"
        />
        <div className="mt-2 text-[11px] text-slate-500">
          Minimum 3 characters. This will show on the timeline.
        </div>
      </Modal>
    </>
  );
}

function decisionHeadline(source?: string | null, msg?: string | null): string {
  const s = (source || "").toUpperCase();
  if (s.includes("COMPLY")) return "Approve compliance exception?";
  if (s.includes("CLEAR")) return "Approve reroute outside of constraints?";
  if (s.includes("LOAD")) return "Approve load plan exception?";
  if (msg) return msg;
  return "A decision is needed before this workflow continues";
}

function decisionContext(source?: string | null, msg?: string | null): string {
  const s = (source || "").toUpperCase();
  if (msg) return msg;
  if (s.includes("COMPLY")) return "Documentation or DG classification outside autonomous tier.";
  if (s.includes("CLEAR")) return "No reroute option satisfied the active constraints.";
  if (s.includes("LOAD")) return "Weight balance or hazmat placement could not be resolved safely.";
  return "See the agent timeline below for the full reasoning.";
}
