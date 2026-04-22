"use client";

import Link from "next/link";
import { useCallback } from "react";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { SystemStatusPill } from "@/components/SystemStatusPill";
import { OrderSummaryHeader } from "@/components/OrderSummaryHeader";
import { AgentTimeline } from "@/components/AgentTimeline";
import { SharedStatePanel } from "@/components/SharedStatePanel";
import { EscalationCard } from "@/components/EscalationCard";
import { GovernanceBadges } from "@/components/GovernanceBadges";
import { WorkflowControls } from "@/components/WorkflowControls";
import { usePolling } from "@/lib/hooks";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import type { OrderDetail } from "@/lib/types";

export default function OrderDetailPage({ params }: { params: { id: string } }) {
  const fetcher = useCallback(() => api.getOrder(params.id), [params.id]);
  const { data, error, loading, lastUpdated, refresh } = usePolling<OrderDetail>(
    fetcher,
    5000,
    [params.id],
  );

  const headerRight = data ? (
    <SystemStatusPill
      active={data.status.toUpperCase() === "RUNNING" ? 1 : 0}
      awaiting={data.escalation.active ? 1 : 0}
      loading={loading && !data}
    />
  ) : null;

  const subnav = (
    <div className="flex items-center justify-between gap-3 text-xs">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All workflows
      </Link>
      <span className="text-slate-500">
        Last refresh: {lastUpdated ? timeAgo(lastUpdated.toISOString()) : "—"} · polling every 5s
      </span>
    </div>
  );

  return (
    <AppShell headerRight={headerRight} subnav={subnav}>
      {error ? (
        <ErrorState message={error.message} onRetry={() => void refresh()} />
      ) : loading && !data ? (
        <LoadingState />
      ) : !data ? (
        <div className="text-sm text-slate-400">No data.</div>
      ) : (
        <Body order={data} refresh={refresh} />
      )}
    </AppShell>
  );
}

function Body({ order, refresh }: { order: OrderDetail; refresh: () => Promise<void> }) {
  return (
    <div className="flex flex-col gap-6">
      {order.escalation.active ? (
        <EscalationCard order={order} onResolved={() => void refresh()} />
      ) : null}

      <OrderSummaryHeader order={order} />

      <WorkflowControls order={order} onAction={() => void refresh()} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr,360px] gap-6">
        <div className="flex flex-col gap-6 min-w-0">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Agent activity</CardTitle>
                <span className="text-[11px] text-slate-500">
                  Chronological decision trail · plain English
                </span>
              </div>
            </CardHeader>
            <CardBody>
              {order.timeline.length === 0 ? (
                <div className="text-sm text-slate-400">
                  No agent activity yet — trigger the workflow above to dispatch CargoComply.
                </div>
              ) : (
                <AgentTimeline order={order} />
              )}
            </CardBody>
          </Card>

          <GovernanceBadges order={order} />
        </div>

        <aside className="lg:sticky lg:top-24 h-fit">
          <SharedStatePanel order={order} />
        </aside>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="py-12 flex items-center justify-center gap-3 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-r-transparent" />
      <span>Fetching the latest agent decisions…</span>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card>
      <CardBody>
        <div className="flex items-start gap-3 text-sm text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="flex-1">
            <div className="font-medium">Couldn&apos;t load this workflow</div>
            <p className="mt-1 text-rose-300/80">
              {message} — the order may not exist, or the backend may be offline.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Button size="sm" variant="secondary" onClick={onRetry}>
                Try again
              </Button>
              <Link
                href="/dashboard"
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                ← Back to dashboard
              </Link>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
