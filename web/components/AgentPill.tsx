import { Boxes, Route, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { agentLabel } from "@/lib/format";

type AgentTone = "comply" | "clear" | "load" | "orch" | "neutral";

const TONES: Record<
  AgentTone,
  { bg: string; text: string; ring: string; icon: JSX.Element }
> = {
  comply: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-300",
    ring: "ring-emerald-400/25",
    icon: <ShieldCheck className="h-3.5 w-3.5" />,
  },
  clear: {
    bg: "bg-sky-500/10",
    text: "text-sky-300",
    ring: "ring-sky-400/25",
    icon: <Route className="h-3.5 w-3.5" />,
  },
  load: {
    bg: "bg-indigo-500/10",
    text: "text-indigo-300",
    ring: "ring-indigo-400/25",
    icon: <Boxes className="h-3.5 w-3.5" />,
  },
  orch: {
    bg: "bg-slate-700/40",
    text: "text-slate-200",
    ring: "ring-slate-500/30",
    icon: <span className="text-[10px] font-semibold tracking-wider">O</span>,
  },
  neutral: {
    bg: "bg-slate-800/60",
    text: "text-slate-300",
    ring: "ring-slate-600/30",
    icon: <span className="text-[10px]">•</span>,
  },
};

function toneFor(raw: string | null | undefined): AgentTone {
  const v = (raw || "").toUpperCase();
  if (v.includes("COMPLY")) return "comply";
  if (v.includes("CLEAR")) return "clear";
  if (v.includes("LOAD")) return "load";
  if (v.includes("ORCH")) return "orch";
  return "neutral";
}

export function AgentPill({
  agent,
  className,
  subtle = false,
}: {
  agent: string | null | undefined;
  className?: string;
  subtle?: boolean;
}) {
  const label = agentLabel(agent);
  const tone = TONES[toneFor(agent)];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ring-1",
        tone.bg,
        tone.text,
        tone.ring,
        subtle && "bg-transparent",
        className,
      )}
    >
      {tone.icon}
      <span>{label}</span>
    </span>
  );
}

export function AgentIconDot({ agent, className }: { agent: string | null | undefined; className?: string }) {
  const tone = TONES[toneFor(agent)];
  return (
    <span
      className={cn(
        "inline-flex h-6 w-6 items-center justify-center rounded-md ring-1",
        tone.bg,
        tone.ring,
        tone.text,
        className,
      )}
    >
      {tone.icon}
    </span>
  );
}
