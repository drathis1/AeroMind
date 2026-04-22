import type { OrderStatus, PayloadPreview } from "./types";

export interface StatusBucket {
  key:
    | "ACTIVE"
    | "AWAITING_HUMAN"
    | "CLOSED_CLEAN"
    | "DG_LOCK"
    | "SANCTIONS_HOLD"
    | "BLAST_RADIUS_CAP"
    | "READY"
    | "IN_TRANSIT"
    | "UNKNOWN";
  label: string;
}

/**
 * Collapse the backend's raw status + payload into one of the UI status
 * buckets described in the design spec. The real demo store only emits a
 * subset of these states; the rest we derive from payload so the UI still
 * surfaces the concept (e.g. DG-on-board → DG Lock evaluated).
 */
export function bucketForOrder(
  status: OrderStatus,
  payload?: PayloadPreview,
): StatusBucket {
  const s = (status || "").toUpperCase();
  if (s === "AWAITING_HUMAN") return { key: "AWAITING_HUMAN", label: "Awaiting human" };
  if (s === "DELIVERED") return { key: "CLOSED_CLEAN", label: "Closed clean" };
  if (s === "IN_TRANSIT") return { key: "IN_TRANSIT", label: "In transit" };
  if (s === "RUNNING") return { key: "ACTIVE", label: "Active" };
  if (s === "READY") return { key: "READY", label: "Ready" };
  if (payload?.hazmat_on_board) return { key: "DG_LOCK", label: "DG review" };
  return { key: "UNKNOWN", label: status || "Unknown" };
}

export const AGENT_LABELS: Record<string, string> = {
  CARGOCOMPLY: "CargoComply",
  CLEARPATH: "ClearPath",
  LOADIQ: "LoadIQ",
  ORCHESTRATOR: "Orchestrator",
};

export function agentLabel(raw: string | null | undefined): string {
  if (!raw) return "—";
  return AGENT_LABELS[raw.toUpperCase()] || raw;
}

export const STAGE_LABELS: Record<string, string> = {
  order_created: "Order created",
  compliance: "Compliance review",
  routing: "Route planning",
  load_opt: "Load optimization",
  in_transit: "In transit",
  delivered: "Delivered",
};

export function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] || stage;
}

/**
 * Plain-English status summary used on the order detail page.
 * Human-centered: explains the current situation, not codes.
 */
export function plainEnglishStatus(order: {
  status: OrderStatus;
  current_stage: string;
  escalation: { active: boolean; source_agent: string | null; message: string | null };
  current_agent: string | null;
  payload_preview: PayloadPreview;
}): string {
  if (order.escalation.active) {
    const src = agentLabel(order.escalation.source_agent);
    const msg = order.escalation.message || "A human decision is required before this can continue.";
    return `${src} paused this workflow. ${msg}`;
  }
  const s = (order.status || "").toUpperCase();
  if (s === "READY") {
    return "Order intake complete. No agent has been dispatched yet — trigger the workflow to start compliance review.";
  }
  if (s === "RUNNING") {
    const who = agentLabel(order.current_agent) || "An agent";
    return `${who} is working on this shipment. No human action needed right now.`;
  }
  if (s === "IN_TRANSIT") {
    return "All agents cleared the workflow. Shipment is moving and will close when delivery is confirmed.";
  }
  if (s === "DELIVERED") {
    return "Shipment delivered. Workflow closed clean — the full decision trail is below for audit.";
  }
  return "Current state surfaced from the orchestrator shared state panel.";
}
