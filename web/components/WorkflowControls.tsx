"use client";

import { useState } from "react";
import { FastForward, Play, StepForward, Truck, Zap } from "lucide-react";
import { Button } from "./ui/Button";
import { api } from "@/lib/api";
import type { InjectKind, OrderDetail } from "@/lib/types";

/**
 * The demo backend exposes step / run-all / inject so ops can walk through
 * the workflow. In production these would be automatic; here they power the
 * demo story.
 */
export function WorkflowControls({
  order,
  onAction,
}: {
  order: OrderDetail;
  onAction?: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wrap =
    <T extends (...args: any[]) => Promise<any>>(name: string, fn: T) =>
    async (...args: Parameters<T>) => {
      setError(null);
      setBusy(name);
      try {
        await fn(...args);
        onAction?.();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(null);
      }
    };

  const trigger = wrap("trigger", () => api.triggerWorkflow(order.id));
  const step = wrap("step", () => api.stepWorkflow(order.id));
  const runAll = wrap("run-all", () => api.runAll(order.id));
  const deliver = wrap("deliver", () => api.completeDelivery(order.id));
  const inject = wrap("inject", (kind: InjectKind) => api.injectEscalation(order.id, kind));

  const status = order.status.toUpperCase();
  const gateOpen = order.escalation.active;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {status === "READY" ? (
          <Button size="sm" onClick={() => void trigger()} loading={busy === "trigger"}>
            <Play className="h-4 w-4" />
            Trigger workflow
          </Button>
        ) : null}

        {status === "RUNNING" && !gateOpen ? (
          <>
            <Button size="sm" variant="secondary" onClick={() => void step()} loading={busy === "step"}>
              <StepForward className="h-4 w-4" />
              Step (1 agent)
            </Button>
            <Button size="sm" onClick={() => void runAll()} loading={busy === "run-all"}>
              <FastForward className="h-4 w-4" />
              Run to next gate
            </Button>
          </>
        ) : null}

        {status === "IN_TRANSIT" ? (
          <Button size="sm" onClick={() => void deliver()} loading={busy === "deliver"}>
            <Truck className="h-4 w-4" />
            Mark delivered
          </Button>
        ) : null}
      </div>

      {status === "RUNNING" && !gateOpen ? (
        <details className="group">
          <summary className="cursor-pointer text-[11px] uppercase tracking-wider text-slate-500 hover:text-slate-300 transition-colors inline-flex items-center gap-1.5">
            <Zap className="h-3 w-3" />
            Demo: inject escalation scenario
          </summary>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void inject("missing_docs")}
              loading={busy === "inject"}
            >
              Missing customs docs
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void inject("route")}
              loading={busy === "inject"}
            >
              Route constraint breach
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void inject("load")}
              loading={busy === "inject"}
            >
              Load / hazmat conflict
            </Button>
          </div>
        </details>
      ) : null}

      {error ? <div className="text-xs text-rose-300">{error}</div> : null}
    </div>
  );
}
