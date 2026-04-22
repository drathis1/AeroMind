import { cn } from "@/lib/utils";

export type StatsTone = "default" | "attention" | "danger" | "success";

export function StatsCard({
  label,
  value,
  hint,
  icon,
  tone = "default",
}: {
  label: string;
  value: number | string;
  hint?: string;
  icon?: React.ReactNode;
  tone?: StatsTone;
}) {
  const toneRing =
    tone === "attention"
      ? "ring-amber-400/30"
      : tone === "danger"
        ? "ring-rose-400/30"
        : tone === "success"
          ? "ring-emerald-400/25"
          : "ring-slate-800";
  const toneDot =
    tone === "attention"
      ? "bg-amber-400"
      : tone === "danger"
        ? "bg-rose-500"
        : tone === "success"
          ? "bg-emerald-400"
          : "bg-sky-400";
  const toneText =
    tone === "attention"
      ? "text-amber-200"
      : tone === "danger"
        ? "text-rose-300"
        : tone === "success"
          ? "text-emerald-300"
          : "text-slate-100";
  return (
    <div className={cn("rounded-xl bg-slate-900/70 ring-1 p-4 flex flex-col gap-3", toneRing)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400">
          <span className={cn("h-2 w-2 rounded-full", toneDot)} />
          {label}
        </div>
        {icon ? <span className="text-slate-400">{icon}</span> : null}
      </div>
      <div className={cn("text-3xl font-semibold tabular-nums", toneText)}>{value}</div>
      {hint ? <div className="text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}
