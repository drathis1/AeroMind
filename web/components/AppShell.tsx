import Link from "next/link";
import { Plane } from "lucide-react";
import { cn } from "@/lib/utils";

export function AppShell({
  children,
  headerRight,
  subnav,
}: {
  children: React.ReactNode;
  headerRight?: React.ReactNode;
  subnav?: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-6 py-3">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="group flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-sky-500/10 ring-1 ring-sky-400/30 text-sky-300 group-hover:bg-sky-500/20 transition-colors">
                <Plane className="h-4 w-4" />
              </span>
              <span className="flex items-baseline gap-2">
                <span className="text-base font-semibold tracking-tight text-slate-50">AeroMind</span>
                <span className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Ops</span>
              </span>
            </Link>
          </div>
          <div className="flex items-center gap-3">{headerRight}</div>
        </div>
        {subnav ? (
          <div className={cn("border-t border-slate-800/60 bg-slate-900/30")}>
            <div className="mx-auto max-w-[1400px] px-6 py-2">{subnav}</div>
          </div>
        ) : null}
      </header>
      <main className="mx-auto max-w-[1400px] px-6 py-6">{children}</main>
    </div>
  );
}
