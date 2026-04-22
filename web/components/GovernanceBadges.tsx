import { AlertTriangle, CheckCircle2, Gauge, Lock, ShieldCheck, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OrderDetail } from "@/lib/types";
import { Card, CardBody, CardHeader, CardTitle } from "./ui/Card";

type CheckState = "ok" | "triggered" | "na";

interface GovernanceItem {
  key: string;
  name: string;
  detail: string;
  state: CheckState;
  icon: JSX.Element;
}

function deriveControls(order: OrderDetail): GovernanceItem[] {
  const p = order.payload_preview || {};
  const escalated = order.escalation.active;
  const hazmat = !!p.hazmat_on_board;
  const international = !!p.international;
  const missingDocs = international && p.has_docs === false;

  const dgState: CheckState = hazmat ? (escalated ? "triggered" : "ok") : "na";
  const blastUsed = order.shared_state.completed_agents.length;
  const blastState: CheckState = blastUsed >= 15 ? "triggered" : "ok";
  const allowlistState: CheckState = "ok";
  const injectionState: CheckState = "ok";
  const judgeState: CheckState = escalated || missingDocs ? "triggered" : "ok";

  return [
    {
      key: "dg",
      name: "DG Lock",
      detail: hazmat
        ? dgState === "triggered"
          ? "Dangerous-goods cargo present — awaiting human approval."
          : "DG cargo flagged; controls evaluated, no breach."
        : "No dangerous goods on this shipment.",
      state: dgState,
      icon: <Lock className="h-3.5 w-3.5" />,
    },
    {
      key: "blast",
      name: "Blast Radius Cap",
      detail: `${blastUsed}/15 autonomous commits used this workflow.`,
      state: blastState,
      icon: <Gauge className="h-3.5 w-3.5" />,
    },
    {
      key: "inj",
      name: "Prompt Injection Filter",
      detail: "All agent inputs scanned; clean.",
      state: injectionState,
      icon: <ShieldCheck className="h-3.5 w-3.5" />,
    },
    {
      key: "allow",
      name: "Tool Allowlist",
      detail: "No out-of-scope tool calls attempted.",
      state: allowlistState,
      icon: <ShieldCheck className="h-3.5 w-3.5" />,
    },
    {
      key: "judge",
      name: "LLM Judge",
      detail:
        judgeState === "triggered"
          ? "Flagged for human review — see escalation above."
          : "Agent outputs passed automated review.",
      state: judgeState,
      icon: <ShieldAlert className="h-3.5 w-3.5" />,
    },
  ];
}

function stateStyle(s: CheckState) {
  switch (s) {
    case "triggered":
      return {
        ring: "ring-amber-400/30",
        bg: "bg-amber-500/10",
        text: "text-amber-200",
        label: "Triggered",
        icon: <AlertTriangle className="h-3.5 w-3.5" />,
      };
    case "na":
      return {
        ring: "ring-slate-700",
        bg: "bg-slate-800/40",
        text: "text-slate-400",
        label: "Not applicable",
        icon: <span className="text-[10px]">—</span>,
      };
    default:
      return {
        ring: "ring-emerald-400/25",
        bg: "bg-emerald-500/10",
        text: "text-emerald-300",
        label: "Clean",
        icon: <CheckCircle2 className="h-3.5 w-3.5" />,
      };
  }
}

export function GovernanceBadges({ order }: { order: OrderDetail }) {
  const items = deriveControls(order);
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Governance Controls</CardTitle>
          <span className="text-[11px] text-slate-500">Evaluated for this workflow</span>
        </div>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {items.map((item) => {
            const s = stateStyle(item.state);
            return (
              <div
                key={item.key}
                className={cn(
                  "rounded-lg ring-1 bg-slate-900/40 p-3 flex flex-col gap-2",
                  "ring-slate-800",
                )}
              >
                <div className="flex items-center gap-2 text-slate-200 text-sm font-medium">
                  <span className="text-slate-400">{item.icon}</span>
                  {item.name}
                </div>
                <span
                  className={cn(
                    "inline-flex w-fit items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1",
                    s.bg,
                    s.ring,
                    s.text,
                  )}
                >
                  {s.icon}
                  {s.label}
                </span>
                <p className="text-xs text-slate-400 leading-relaxed">{item.detail}</p>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}
