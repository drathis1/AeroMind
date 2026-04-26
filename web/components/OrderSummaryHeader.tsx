import { AlertTriangle, Building2, Factory, Package, PackageCheck, Truck, Weight } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { OrderDetail } from "@/lib/types";
import { plainEnglishStatus } from "@/lib/format";

export function OrderSummaryHeader({ order }: { order: OrderDetail }) {
  const p = order.payload_preview || {};
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400">
            <Package className="h-3.5 w-3.5" />
            Order {order.id}
          </div>
          <h1 className="mt-1 text-2xl font-semibold text-slate-50 flex items-center gap-3">
            <span className="font-mono">{order.origin || "—"}</span>
            <span className="text-slate-500">→</span>
            <span className="font-mono">{order.destination || "—"}</span>
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={order.status} payload={p} />
          {p.hazmat_on_board ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300 ring-1 ring-rose-400/25">
              <AlertTriangle className="h-3 w-3" />
              DG on board
            </span>
          ) : null}
          {p.international ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-2.5 py-1 text-xs font-medium text-sky-300 ring-1 ring-sky-400/25">
              International
            </span>
          ) : null}
        </div>
      </div>

      <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
        {plainEnglishStatus(order)}
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetaTile
          icon={<Truck className="h-3.5 w-3.5" />}
          label="Shipper"
          value={order.shipper || "—"}
        />
        <MetaTile
          icon={<Factory className="h-3.5 w-3.5" />}
          label="Manufacturer"
          value={order.manufacturer || "—"}
        />
        <MetaTile
          icon={<Building2 className="h-3.5 w-3.5" />}
          label="Supplier"
          value={order.supplier || "—"}
        />
        <MetaTile
          icon={<Weight className="h-3.5 w-3.5" />}
          label="Weight"
          value={p.weight_kg != null ? `${p.weight_kg.toLocaleString()} kg` : "—"}
        />
      </div>
    </div>
  );
}

function MetaTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-sm text-slate-200 truncate">{value}</div>
    </div>
  );
}
