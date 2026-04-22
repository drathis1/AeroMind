"use client";

import { cn } from "@/lib/utils";

export function SystemStatusPill({
  active,
  awaiting,
  loading,
}: {
  active: number;
  awaiting: number;
  loading?: boolean;
}) {
  const tone = awaiting > 0 ? "amber" : active > 0 ? "sky" : "slate";
  const dot =
    tone === "amber" ? "bg-amber-400" : tone === "sky" ? "bg-sky-400" : "bg-slate-500";
  const text =
    tone === "amber" ? "text-amber-200" : tone === "sky" ? "text-sky-200" : "text-slate-300";
  const ring =
    tone === "amber" ? "ring-amber-400/30" : tone === "sky" ? "ring-sky-400/30" : "ring-slate-600/40";
  const bg =
    tone === "amber" ? "bg-amber-500/10" : tone === "sky" ? "bg-sky-500/10" : "bg-slate-800/50";

  const label =
    awaiting > 0
      ? `${awaiting} awaiting human`
      : active > 0
        ? `${active} active workflow${active === 1 ? "" : "s"}`
        : "All clear";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ring-1",
        bg,
        text,
        ring,
      )}
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2">
        {tone !== "slate" ? (
          <span className={cn("absolute inline-flex h-full w-full rounded-full animate-ping-soft", dot)} />
        ) : null}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", dot)} />
      </span>
      <span>{label}</span>
      {loading ? <span className="text-slate-500">· syncing</span> : null}
    </span>
  );
}
