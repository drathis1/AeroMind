import { cn } from "@/lib/utils";

export type ConfidenceLevel = "high" | "medium" | "low";

const TONES: Record<ConfidenceLevel, { bg: string; text: string; ring: string; label: string }> = {
  high: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-300",
    ring: "ring-emerald-400/25",
    label: "High confidence",
  },
  medium: {
    bg: "bg-amber-500/10",
    text: "text-amber-200",
    ring: "ring-amber-400/25",
    label: "Medium confidence",
  },
  low: {
    bg: "bg-rose-500/10",
    text: "text-rose-300",
    ring: "ring-rose-400/25",
    label: "Low confidence",
  },
};

export function ConfidenceChip({
  level,
  note,
  className,
}: {
  level: ConfidenceLevel;
  note?: string;
  className?: string;
}) {
  const t = TONES[level];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1",
        t.bg,
        t.text,
        t.ring,
        className,
      )}
      title={note || t.label}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full",
        level === "high" ? "bg-emerald-400" : level === "medium" ? "bg-amber-400" : "bg-rose-500",
      )} />
      {t.label}
      {note ? <span className="font-normal text-slate-400">— {note}</span> : null}
    </span>
  );
}
