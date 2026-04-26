"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "./ui/Button";
import { Modal } from "./ui/Modal";
import { api } from "@/lib/api";
import type { CreateOrderBody } from "@/lib/types";
import { cn } from "@/lib/utils";

type EventType = "NEW_BOOKING" | "WEATHER_ALERT" | "MANIFEST_CHANGE";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: (id: string) => void;
}

export function NewOrderModal({ open, onClose, onCreated }: Props) {
  const router = useRouter();
  const [eventType, setEventType] = useState<EventType>("NEW_BOOKING");
  const [origin, setOrigin] = useState("JFK");
  const [destination, setDestination] = useState("LAX");
  const [value, setValue] = useState("125000");
  const [weight, setWeight] = useState("2400");
  const [international, setInternational] = useState(false);
  const [dg, setDg] = useState(false);
  const [rerouteNewCountry, setRerouteNewCountry] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    origin.trim().length > 0 && destination.trim().length > 0 && !submitting;

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      // Map UI fields → backend CreateOrderBody. The demo API models the
      // event type implicitly via payload + the /workflow/trigger call.
      const body: CreateOrderBody = {
        origin: origin.trim().toUpperCase(),
        destination: destination.trim().toUpperCase(),
        international: international || rerouteNewCountry,
        weight_kg: Number(weight) || 0,
        has_docs: true,
        route_stays_in_country: !rerouteNewCountry && !international,
        delay_hours: eventType === "WEATHER_ALERT" ? 8 : 2,
        hazmat_on_board: dg,
      };
      const { id } = await api.createOrder(body);
      // Trigger the workflow so agents actually start working.
      try {
        await api.triggerWorkflow(id);
      } catch {
        /* not fatal — dashboard will still show the order */
      }
      onClose();
      onCreated?.(id);
      router.push(`/orders/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={submitting ? () => {} : onClose}
      title="Start a new workflow"
      description="Register a cargo event. The orchestrator will dispatch the right agents; you'll be paged only if a human decision is needed."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!canSubmit} loading={submitting}>
            Create &amp; trigger
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Field label="Event type" hint="What triggered this workflow?">
          <div className="grid grid-cols-3 gap-2">
            {(["NEW_BOOKING", "WEATHER_ALERT", "MANIFEST_CHANGE"] as EventType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setEventType(t)}
                className={cn(
                  "rounded-md border px-3 py-2 text-xs font-medium transition-colors",
                  eventType === t
                    ? "border-sky-400/50 bg-sky-500/10 text-sky-200"
                    : "border-slate-700 bg-slate-900/60 text-slate-300 hover:border-slate-600",
                )}
              >
                {t.replace("_", " ")}
              </button>
            ))}
          </div>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Origin (IATA)">
            <Input value={origin} onChange={(v) => setOrigin(v.toUpperCase())} maxLength={5} />
          </Field>
          <Field label="Destination (IATA)">
            <Input value={destination} onChange={(v) => setDestination(v.toUpperCase())} maxLength={5} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Declared value (USD)">
            <Input value={value} onChange={setValue} inputMode="numeric" />
          </Field>
          <Field label="Weight (kg)">
            <Input value={weight} onChange={setWeight} inputMode="numeric" />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <Toggle
            label="Dangerous goods (DG) on board"
            help="Triggers DG Lock evaluation and may require human approval."
            checked={dg}
            onChange={setDg}
            tone="danger"
          />
          <Toggle
            label="Reroute crosses into a new country"
            help="Activates cross-border compliance review before any booking commit."
            checked={rerouteNewCountry}
            onChange={(v) => {
              setRerouteNewCountry(v);
              if (v) setInternational(true);
            }}
            tone="warning"
          />
          <Toggle
            label="International shipment"
            help="Enables customs documentation checks."
            checked={international}
            onChange={setInternational}
          />
        </div>

        {error ? (
          <div className="flex items-start gap-2 rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
        {label}
      </span>
      {children}
      {hint ? <span className="text-[11px] text-slate-500">{hint}</span> : null}
    </label>
  );
}

function Input({
  value,
  onChange,
  inputMode,
  maxLength,
}: {
  value: string;
  onChange: (v: string) => void;
  inputMode?: "numeric" | "text";
  maxLength?: number;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      inputMode={inputMode}
      maxLength={maxLength}
      className="h-9 rounded-md border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none focus:border-sky-400/60 focus:ring-1 focus:ring-sky-400/40 transition-colors"
    />
  );
}

function Toggle({
  label,
  help,
  checked,
  onChange,
  tone = "default",
}: {
  label: string;
  help?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  tone?: "default" | "warning" | "danger";
}) {
  const activeBg =
    tone === "danger" ? "bg-rose-500" : tone === "warning" ? "bg-amber-400" : "bg-sky-500";
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={cn(
        "flex items-start gap-3 rounded-md border px-3 py-2 text-left transition-colors",
        checked
          ? "border-slate-700 bg-slate-900/60"
          : "border-slate-800 bg-slate-900/30 hover:border-slate-700",
      )}
    >
      <span
        className={cn(
          "mt-0.5 inline-flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors",
          checked ? activeBg : "bg-slate-700",
        )}
      >
        <span
          className={cn(
            "h-4 w-4 rounded-full bg-slate-950 shadow transition-transform",
            checked ? "translate-x-4" : "translate-x-0",
          )}
        />
      </span>
      <span className="flex flex-col">
        <span className="text-sm text-slate-200">{label}</span>
        {help ? <span className="text-[11px] text-slate-500">{help}</span> : null}
      </span>
    </button>
  );
}
