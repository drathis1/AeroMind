"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "warning";
type Size = "sm" | "md" | "lg";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-sky-500 hover:bg-sky-400 text-slate-950 font-medium shadow-sm shadow-sky-500/20 focus-visible:ring-sky-400/60",
  secondary:
    "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 focus-visible:ring-slate-500/60",
  ghost:
    "bg-transparent hover:bg-slate-800/70 text-slate-300 focus-visible:ring-slate-500/60",
  danger:
    "bg-rose-600 hover:bg-rose-500 text-white font-medium focus-visible:ring-rose-400/60",
  warning:
    "bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold focus-visible:ring-amber-300/60",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-sm rounded-md",
  md: "h-9 px-4 text-sm rounded-md",
  lg: "h-11 px-5 text-base rounded-lg",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "primary", size = "md", loading, disabled, children, ...props },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center gap-2 transition-colors outline-none focus-visible:ring-2 disabled:opacity-50 disabled:cursor-not-allowed",
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      >
        {loading ? (
          <span
            aria-hidden
            className="h-3.5 w-3.5 rounded-full border-2 border-current border-r-transparent animate-spin"
          />
        ) : null}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
