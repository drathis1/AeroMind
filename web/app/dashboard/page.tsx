"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronRight,
  Inbox,
  Plus,
  Radio,
  ShieldAlert,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { StatsCard } from "@/components/StatsCard";
import { StatusBadge } from "@/components/StatusBadge";
import { AgentPill } from "@/components/AgentPill";
import { SystemStatusPill } from "@/components/SystemStatusPill";
import { NewOrderModal } from "@/components/NewOrderModal";
import { usePolling } from "@/lib/hooks";
import { api } from "@/lib/api";
import { bucketForOrder } from "@/lib/format";
import { timeAgo } from "@/lib/utils";
import type { OrderSummary } from "@/lib/types";

export default function DashboardPage() {
  const { data, error, loading, lastUpdated, refresh } = usePolling<OrderSummary[]>(
    api.listOrders,
    5000,
  );
  const [newOpen, setNewOpen] = useState(false);

  const stats = useMemo(() => computeStats(data || []), [data]);

  const headerRight = (
    <>
      <SystemStatusPill
        active={stats.active}
        awaiting={stats.awaiting}
        loading={loading && !data}
      />
      <Button size="sm" variant="primary" onClick={() => setNewOpen(true)}>
        <Plus className="h-4 w-4" />
        New workflow
      </Button>
    </>
  );

  return (
    <AppShell headerRight={headerRight}>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
              Operations dashboard
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              Live view of every cargo workflow. Amber rows need you — the rest are being handled
              autonomously by LoadIQ, ClearPath and CargoComply.
            </p>
          </div>
          <div className="text-xs text-slate-500 whitespace-nowrap mt-2">
            Last refresh: {lastUpdated ? timeAgo(lastUpdated.toISOString()) : "—"}
          </div>
        </div>

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatsCard
            label="Active workflows"
            value={stats.active}
            hint="Agents currently running"
            icon={<Radio className="h-4 w-4" />}
          />
          <StatsCard
            label="Awaiting human review"
            value={stats.awaiting}
            hint={stats.awaiting > 0 ? "Needs your decision" : "No pending decisions"}
            icon={<Bell className="h-4 w-4" />}
            tone={stats.awaiting > 0 ? "attention" : "default"}
          />
          <StatsCard
            label="Blocked"
            value={stats.blocked}
            hint="DG lock / sanctions / cap"
            icon={<ShieldAlert className="h-4 w-4" />}
            tone={stats.blocked > 0 ? "danger" : "default"}
          />
          <StatsCard
            label="Closed clean today"
            value={stats.delivered}
            hint="Delivered with full audit"
            icon={<CheckCircle2 className="h-4 w-4" />}
            tone="success"
          />
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase">
                Workflows
              </h2>
              <span className="text-xs text-slate-500">
                {data ? `${data.length} total` : "loading…"} · polling every 5s
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => void refresh()}>
              Refresh
            </Button>
          </div>

          {error ? (
            <ErrorState message={error.message} onRetry={() => void refresh()} />
          ) : loading && !data ? (
            <LoadingState />
          ) : !data || data.length === 0 ? (
            <EmptyState onNew={() => setNewOpen(true)} />
          ) : (
            <OrdersTable orders={data} />
          )}
        </section>
      </div>

      <NewOrderModal open={newOpen} onClose={() => setNewOpen(false)} />
    </AppShell>
  );
}

function OrdersTable({ orders }: { orders: OrderSummary[] }) {
  // Surface AWAITING_HUMAN rows first, then ACTIVE, then the rest.
  const sorted = [...orders].sort((a, b) => priorityRank(a) - priorityRank(b));

  return (
    <div className="overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/60 text-[11px] uppercase tracking-wider text-slate-400">
          <tr>
            <th className="px-5 py-3 text-left font-medium">Order</th>
            <th className="px-5 py-3 text-left font-medium">Route</th>
            <th className="px-5 py-3 text-left font-medium">Status</th>
            <th className="px-5 py-3 text-left font-medium">Agent activity</th>
            <th className="px-5 py-3 text-right font-medium">&nbsp;</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((o) => {
            const bucket = bucketForOrder(o.status);
            const highlight = bucket.key === "AWAITING_HUMAN";
            return (
              <tr
                key={o.id}
                className={
                  "border-t border-slate-800/80 hover:bg-slate-800/30 transition-colors " +
                  (highlight ? "bg-amber-500/[0.04]" : "")
                }
              >
                <td className="px-5 py-3">
                  <Link
                    href={`/orders/${o.id}`}
                    className="font-mono text-sm text-slate-100 hover:text-sky-300 transition-colors"
                  >
                    {o.id}
                  </Link>
                </td>
                <td className="px-5 py-3 text-slate-200">{o.route}</td>
                <td className="px-5 py-3">
                  <StatusBadge status={o.status} />
                </td>
                <td className="px-5 py-3">
                  {o.current_agent ? (
                    <AgentPill agent={o.current_agent} />
                  ) : (
                    <span className="text-xs text-slate-500">Idle</span>
                  )}
                </td>
                <td className="px-5 py-3 text-right">
                  <Link
                    href={`/orders/${o.id}`}
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-sky-300 transition-colors"
                  >
                    Open
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function priorityRank(o: OrderSummary): number {
  const b = bucketForOrder(o.status);
  if (b.key === "AWAITING_HUMAN") return 0;
  if (b.key === "DG_LOCK" || b.key === "SANCTIONS_HOLD" || b.key === "BLAST_RADIUS_CAP") return 1;
  if (b.key === "ACTIVE") return 2;
  if (b.key === "IN_TRANSIT") return 3;
  if (b.key === "READY") return 4;
  if (b.key === "CLOSED_CLEAN") return 5;
  return 6;
}

function computeStats(orders: OrderSummary[]) {
  let active = 0;
  let awaiting = 0;
  let delivered = 0;
  let blocked = 0;
  for (const o of orders) {
    const b = bucketForOrder(o.status);
    if (b.key === "ACTIVE") active++;
    else if (b.key === "AWAITING_HUMAN") {
      awaiting++;
      active++;
    } else if (b.key === "IN_TRANSIT") active++;
    else if (b.key === "CLOSED_CLEAN") delivered++;
    else if (b.key === "DG_LOCK" || b.key === "SANCTIONS_HOLD" || b.key === "BLAST_RADIUS_CAP") {
      blocked++;
    }
  }
  return { active, awaiting, delivered, blocked };
}

function LoadingState() {
  return (
    <div className="px-5 py-10 text-sm text-slate-400 flex items-center gap-3">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-400 border-r-transparent" />
      Loading workflows from the orchestrator…
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="px-6 py-12 flex flex-col items-center text-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-md bg-slate-800/60 ring-1 ring-slate-700 text-slate-400">
        <Inbox className="h-5 w-5" />
      </span>
      <div className="max-w-md">
        <div className="text-sm font-medium text-slate-100">No workflows yet</div>
        <p className="text-xs text-slate-400 mt-1">
          Workflows start when a cargo event arrives — a new booking, a weather alert, or a
          manifest change. Kick one off to see the agents coordinate in real time.
        </p>
      </div>
      <Button size="sm" onClick={onNew}>
        <Plus className="h-4 w-4" /> Trigger a workflow
      </Button>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="px-5 py-10 flex items-start gap-3 text-sm text-rose-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <div className="font-medium">Can&apos;t reach the orchestrator</div>
        <p className="mt-1 text-rose-300/80">
          {message} — make sure the FastAPI backend is running at{" "}
          <code className="font-mono text-xs">http://localhost:8000</code>.
        </p>
        <div className="mt-3">
          <Button size="sm" variant="secondary" onClick={onRetry}>
            Try again
          </Button>
        </div>
      </div>
    </div>
  );
}
