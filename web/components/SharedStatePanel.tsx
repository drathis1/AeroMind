import { cn } from "@/lib/utils";
import { agentLabel, stageLabel } from "@/lib/format";
import { formatTime } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardTitle } from "./ui/Card";
import type { OrderDetail } from "@/lib/types";

/**
 * Human-readable view of the orchestrator's shared state — NOT raw JSON.
 * Every key maps to a labeled, plain-English field.
 */
export function SharedStatePanel({ order }: { order: OrderDetail }) {
  const s = order.shared_state;
  const p = order.payload_preview || {};

  const rerouteConfirmed = Boolean(
    (order.agent_results?.CLEARPATH as any)?.handoff?.reroute_complete,
  );
  const complianceStatus =
    (order.agent_results?.CARGOCOMPLY as any)?.status || "pending";
  const loadStatus =
    (order.agent_results?.LOADIQ as any)?.weight_balance_ok === true
      ? "passed"
      : (order.agent_results?.LOADIQ as any)?.escalation_required
        ? "blocked"
        : "pending";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Shared state</CardTitle>
        <p className="mt-1 text-[11px] text-slate-500">
          What the orchestrator currently sees. All agents read and write through here — they never
          call each other directly.
        </p>
      </CardHeader>
      <CardBody>
        <dl className="divide-y divide-slate-800">
          <Row label="Current stage" value={stageLabel(s.current_stage)} />
          <Row
            label="Active agent"
            value={
              s.active_agent ? (
                <span className="text-slate-100">{agentLabel(s.active_agent)}</span>
              ) : (
                <span className="text-slate-500">Idle</span>
              )
            }
          />
          <Row
            label="Escalation flag"
            value={
              <FlagPill on={s.escalation_flag} on_label="Raised" off_label="Clear" tone="amber" />
            }
          />
          <Row
            label="Completed agents"
            value={
              s.completed_agents.length === 0 ? (
                <span className="text-slate-500">None yet</span>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {s.completed_agents.map((a) => (
                    <span
                      key={a}
                      className="inline-flex items-center gap-1 rounded-md bg-slate-800/70 px-1.5 py-0.5 text-[11px] text-slate-300 ring-1 ring-slate-700"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      {agentLabel(a)}
                    </span>
                  ))}
                </div>
              )
            }
          />
          <Row
            label="Reroute confirmed"
            value={<FlagPill on={rerouteConfirmed} on_label="Yes" off_label="No" tone="sky" />}
          />
          <Row
            label="DG shipment"
            value={<FlagPill on={!!p.hazmat_on_board} on_label="Yes" off_label="No" tone="rose" />}
          />
          <Row
            label="Compliance status"
            value={<StatusPill value={complianceStatus} />}
          />
          <Row
            label="Load plan status"
            value={<StatusPill value={loadStatus} />}
          />
        </dl>

        {s.orchestrator_notes.length > 0 ? (
          <div className="mt-5 border-t border-slate-800 pt-4">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">
              Orchestrator notes
            </div>
            <ol className="space-y-1.5">
              {s.orchestrator_notes.slice(-6).map((note, i) => {
                const m = note.match(/^\[([^\]]+)\]\s*(.*)$/);
                return (
                  <li key={i} className="text-xs text-slate-400 leading-relaxed">
                    <span className="text-[10px] text-slate-500 mr-1.5">
                      {m ? formatTime(m[1]) : ""}
                    </span>
                    {m ? m[2] : note}
                  </li>
                );
              })}
            </ol>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="text-sm text-slate-200 text-right max-w-[55%]">{value}</dd>
    </div>
  );
}

function FlagPill({
  on,
  on_label,
  off_label,
  tone,
}: {
  on: boolean;
  on_label: string;
  off_label: string;
  tone: "amber" | "sky" | "rose" | "emerald";
}) {
  const onStyles: Record<typeof tone, string> = {
    amber: "bg-amber-500/15 text-amber-200 ring-amber-400/30",
    sky: "bg-sky-500/15 text-sky-200 ring-sky-400/30",
    rose: "bg-rose-500/15 text-rose-200 ring-rose-400/30",
    emerald: "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium ring-1",
        on ? onStyles[tone] : "bg-slate-800/60 text-slate-400 ring-slate-700",
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          on
            ? tone === "amber"
              ? "bg-amber-400"
              : tone === "sky"
                ? "bg-sky-400"
                : tone === "rose"
                  ? "bg-rose-500"
                  : "bg-emerald-400"
            : "bg-slate-500",
        )}
      />
      {on ? on_label : off_label}
    </span>
  );
}

function StatusPill({ value }: { value: string }) {
  const v = (value || "").toLowerCase();
  const styles =
    v === "pass" || v === "passed"
      ? "bg-emerald-500/10 text-emerald-300 ring-emerald-400/25"
      : v === "hold" || v === "blocked"
        ? "bg-amber-500/10 text-amber-200 ring-amber-400/30"
        : "bg-slate-800/60 text-slate-400 ring-slate-700";
  const label =
    v === "pass"
      ? "Passed"
      : v === "passed"
        ? "Passed"
        : v === "hold"
          ? "On hold"
          : v === "blocked"
            ? "Blocked"
            : v === "pending"
              ? "Pending"
              : value || "—";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ring-1",
        styles,
      )}
    >
      {label}
    </span>
  );
}
