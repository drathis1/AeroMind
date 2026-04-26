/**
 * Types mirroring aeromind/demo/models.py + demo/api.py.
 * Server is source of truth; keep these in sync if the backend shape changes.
 */

export type AgentKey = "CARGOCOMPLY" | "CLEARPATH" | "LOADIQ";
export type AgentDisplayName = "CargoComply" | "ClearPath" | "LoadIQ";

export type StepStatus = "pending" | "running" | "done" | "failed";

/** Union of status strings used by the demo store. */
export type OrderStatus =
  | "READY"
  | "RUNNING"
  | "AWAITING_HUMAN"
  | "IN_TRANSIT"
  | "DELIVERED"
  | string;

export interface OrderSummary {
  id: string;
  route: string;
  status: OrderStatus;
  current_agent: string | null;
}

export interface TimelineStep {
  id: string;
  label: string;
  agent: AgentDisplayName | null;
  lane: string;
  status: StepStatus;
}

export interface SharedStateView {
  current_stage: string;
  active_agent: string | null;
  completed_agents: string[];
  escalation_flag: boolean;
  escalation_reason: string | null;
  orchestrator_notes: string[];
}

export interface EscalationInfo {
  active: boolean;
  source_agent: string | null;
  message: string | null;
}

export interface PayloadPreview {
  international?: boolean | null;
  weight_kg?: number | null;
  has_docs?: boolean | null;
  route_stays_in_country?: boolean | null;
  delay_hours?: number | null;
  hazmat_on_board?: boolean | null;
  demo_escalation?: string | null;
  [k: string]: unknown;
}

export interface OrderDetail {
  id: string;
  route: string;
  origin: string;
  destination: string;
  shipper: string;
  manufacturer: string;
  supplier: string;
  status: OrderStatus;
  current_agent: string | null;
  current_stage: string;
  shared_state: SharedStateView;
  timeline: TimelineStep[];
  agent_logs: Record<string, string[]>;
  escalation: EscalationInfo;
  payload_preview: PayloadPreview;
  agent_results: Record<string, unknown>;
  workflow_id: string;
}

export interface CreateOrderBody {
  origin?: string;
  destination?: string;
  international?: boolean;
  weight_kg?: number;
  has_docs?: boolean;
  route_stays_in_country?: boolean;
  delay_hours?: number;
  hazmat_on_board?: boolean;
}

export type EscalationAction = "approve" | "resolve" | "override";
export interface EscalationActionBody {
  action: EscalationAction;
  note?: string | null;
}

export type InjectKind = "missing_docs" | "route" | "load";
