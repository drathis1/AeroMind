import { AlertTriangle, Bell, CheckCircle2, Loader2, Lock, Plane } from "lucide-react";
import { cn } from "@/lib/utils";
import { bucketForOrder, type StatusBucket } from "@/lib/format";
import type { OrderStatus, PayloadPreview } from "@/lib/types";

interface StatusBadgeProps {
  status: OrderStatus;
  payload?: PayloadPreview;
  className?: string;
  size?: "sm" | "md";
}

function bucketStyle(bucket: StatusBucket["key"]): {
  ring: string;
  dot: string;
  text: string;
  bg: string;
  icon: JSX.Element | null;
} {
  switch (bucket) {
    case "ACTIVE":
      return {
        ring: "ring-sky-400/25",
        dot: "bg-sky-400",
        text: "text-sky-300",
        bg: "bg-sky-500/10",
        icon: <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full rounded-full bg-sky-400 animate-ping-soft" /><span className="relative inline-flex h-2 w-2 rounded-full bg-sky-400" /></span>,
      };
    case "AWAITING_HUMAN":
      return {
        ring: "ring-amber-400/30",
        dot: "bg-amber-400",
        text: "text-amber-200",
        bg: "bg-amber-500/10",
        icon: <Bell className="h-3 w-3" />,
      };
    case "CLOSED_CLEAN":
      return {
        ring: "ring-emerald-400/25",
        dot: "bg-emerald-400",
        text: "text-emerald-300",
        bg: "bg-emerald-500/10",
        icon: <CheckCircle2 className="h-3 w-3" />,
      };
    case "DG_LOCK":
    case "SANCTIONS_HOLD":
      return {
        ring: "ring-rose-400/25",
        dot: "bg-rose-500",
        text: "text-rose-300",
        bg: "bg-rose-500/10",
        icon: <Lock className="h-3 w-3" />,
      };
    case "BLAST_RADIUS_CAP":
      return {
        ring: "ring-amber-400/25",
        dot: "bg-amber-400",
        text: "text-amber-200",
        bg: "bg-amber-500/10",
        icon: <AlertTriangle className="h-3 w-3" />,
      };
    case "IN_TRANSIT":
      return {
        ring: "ring-sky-400/20",
        dot: "bg-sky-400",
        text: "text-sky-300",
        bg: "bg-sky-500/10",
        icon: <Plane className="h-3 w-3" />,
      };
    case "READY":
      return {
        ring: "ring-slate-600/40",
        dot: "bg-slate-400",
        text: "text-slate-300",
        bg: "bg-slate-800/60",
        icon: null,
      };
    default:
      return {
        ring: "ring-slate-600/40",
        dot: "bg-slate-500",
        text: "text-slate-300",
        bg: "bg-slate-800/60",
        icon: <Loader2 className="h-3 w-3" />,
      };
  }
}

export function StatusBadge({ status, payload, className, size = "md" }: StatusBadgeProps) {
  const bucket = bucketForOrder(status, payload);
  const s = bucketStyle(bucket.key);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full ring-1 font-medium tracking-wide",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
        s.bg,
        s.ring,
        s.text,
        className,
      )}
      title={bucket.label}
    >
      {s.icon ?? <span className={cn("h-2 w-2 rounded-full", s.dot)} />}
      <span className="uppercase">{bucket.label}</span>
    </span>
  );
}
