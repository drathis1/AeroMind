import type {
  CreateOrderBody,
  EscalationActionBody,
  InjectKind,
  OrderDetail,
  OrderSummary,
} from "./types";

/**
 * All requests hit Next.js at `/api/*`, which `next.config.js` rewrites to the
 * FastAPI backend (default http://localhost:8000). That avoids CORS and keeps
 * the frontend portable.
 */

const BASE = "";

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `API ${init.method || "GET"} ${path} failed: ${res.status} ${res.statusText}${
        body ? ` — ${body.slice(0, 200)}` : ""
      }`,
    );
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  listOrders: () => request<OrderSummary[]>("/api/demo/orders"),
  getOrder: (id: string) => request<OrderDetail>(`/api/demo/orders/${id}`),
  createOrder: (body: CreateOrderBody) =>
    request<{ id: string }>("/api/demo/orders", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  triggerWorkflow: (id: string) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/workflow/trigger`,
      { method: "POST" },
    ),
  stepWorkflow: (id: string) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/workflow/step`,
      { method: "POST" },
    ),
  runAll: (id: string) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/workflow/run-all`,
      { method: "POST" },
    ),
  completeDelivery: (id: string) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/delivery/complete`,
      { method: "POST" },
    ),
  injectEscalation: (id: string, kind: InjectKind) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/escalation/inject`,
      { method: "POST", body: JSON.stringify({ kind }) },
    ),
  resolveEscalation: (id: string, body: EscalationActionBody) =>
    request<{ ok: boolean; order: OrderDetail }>(
      `/api/demo/orders/${id}/escalation/resolve`,
      { method: "POST", body: JSON.stringify(body) },
    ),
};
