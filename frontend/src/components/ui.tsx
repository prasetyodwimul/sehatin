"use client";

import { useEffect, useId, useRef, useState } from "react";

/* ---------------------------------------------------------------------- */
/* Button                                                                   */
/* ---------------------------------------------------------------------- */

import { getButtonClasses, type ButtonSize, type ButtonVariant } from "./button-styles";

export function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  loadingLabel,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  loadingLabel?: string;
}) {
  return (
    <button
      className={getButtonClasses({ variant, size, className })}
      disabled={isLoading || props.disabled}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      )}
      {isLoading ? loadingLabel ?? children : children}
    </button>
  );
}

/* ---------------------------------------------------------------------- */
/* Field wrapper shared by Input / Select / Textarea                        */
/* ---------------------------------------------------------------------- */

function FieldShell({
  label,
  helperText,
  error,
  required,
  htmlFor,
  children,
}: {
  label: string;
  helperText?: string;
  error?: string;
  required?: boolean;
  htmlFor: string;
  children: React.ReactNode;
}) {
  const helperId = `${htmlFor}-helper`;
  const errorId = `${htmlFor}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-text">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {children}
      {helperText && !error && (
        <p id={helperId} className="text-xs text-muted">
          {helperText}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-medium text-error">
          {error}
        </p>
      )}
    </div>
  );
}

const fieldBaseClasses =
  "min-h-11 w-full rounded-sm border bg-surface px-3 py-2.5 text-sm text-text placeholder:text-muted focus-visible:outline-none";

export function Input({
  label,
  helperText,
  error,
  required,
  id,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  helperText?: string;
  error?: string;
}) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell label={label} helperText={helperText} error={error} required={required} htmlFor={fieldId}>
      <input
        id={fieldId}
        aria-describedby={error ? `${fieldId}-error` : helperText ? `${fieldId}-helper` : undefined}
        aria-invalid={!!error}
        className={`${fieldBaseClasses} ${error ? "border-error" : "border-slate-300"}`}
        {...props}
      />
    </FieldShell>
  );
}

export function Textarea({
  label,
  helperText,
  error,
  required,
  id,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  helperText?: string;
  error?: string;
}) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell label={label} helperText={helperText} error={error} required={required} htmlFor={fieldId}>
      <textarea
        id={fieldId}
        aria-describedby={error ? `${fieldId}-error` : helperText ? `${fieldId}-helper` : undefined}
        aria-invalid={!!error}
        rows={5}
        className={`${fieldBaseClasses} ${error ? "border-error" : "border-slate-300"}`}
        {...props}
      />
    </FieldShell>
  );
}

export function Select({
  label,
  helperText,
  error,
  required,
  id,
  options,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  helperText?: string;
  error?: string;
  options: { label: string; value: string }[];
}) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell label={label} helperText={helperText} error={error} required={required} htmlFor={fieldId}>
      <select
        id={fieldId}
        aria-describedby={error ? `${fieldId}-error` : helperText ? `${fieldId}-helper` : undefined}
        aria-invalid={!!error}
        className={`${fieldBaseClasses} ${error ? "border-error" : "border-slate-300"}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

/* ---------------------------------------------------------------------- */
/* Card                                                                     */
/* ---------------------------------------------------------------------- */

export function Card({
  children,
  padding = "md",
  interactive = false,
  large = false,
  className = "",
}: {
  children: React.ReactNode;
  padding?: "sm" | "md" | "lg";
  interactive?: boolean;
  large?: boolean;
  className?: string;
}) {
  const paddingClasses = { sm: "p-4", md: "p-6", lg: "p-8" }[padding];
  return (
    <div
      className={`min-w-0 border border-slate-200 bg-surface shadow-subtle ${large ? "rounded-3xl" : "rounded-2xl"} ${paddingClasses} ${
        interactive ? "transition-shadow hover:shadow-md" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Badge (never color-only — always icon/symbol + text)                    */
/* ---------------------------------------------------------------------- */

type BadgeVariant = "neutral" | "success" | "warning" | "error" | "info";

const badgeVariantClasses: Record<BadgeVariant, string> = {
  neutral: "bg-slate-100 text-secondary",
  success: "bg-green-50 text-success",
  warning: "bg-amber-50 text-warning",
  error: "bg-red-50 text-error",
  info: "bg-blue-50 text-info",
};

const badgeSymbol: Record<BadgeVariant, string> = {
  neutral: "•",
  success: "✓",
  warning: "!",
  error: "✕",
  info: "ℹ",
};

export function Badge({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${badgeVariantClasses[variant]}`}
    >
      <span aria-hidden="true">{badgeSymbol[variant]}</span>
      {children}
    </span>
  );
}

/* ---------------------------------------------------------------------- */
/* Alert                                                                    */
/* ---------------------------------------------------------------------- */

type AlertVariant = "info" | "warning" | "error" | "success";

const alertVariantClasses: Record<AlertVariant, string> = {
  info: "bg-blue-50 border-info text-info",
  warning: "bg-amber-50 border-warning text-warning",
  error: "bg-red-50 border-error text-error",
  success: "bg-green-50 border-success text-success",
};

export function Alert({
  title,
  children,
  variant = "info",
}: {
  title?: string;
  children: React.ReactNode;
  variant?: AlertVariant;
}) {
  return (
    <div role={variant === "error" ? "alert" : "status"} aria-live={variant === "error" ? "assertive" : "polite"} className={`min-w-0 rounded-2xl border border-l-4 p-4 text-sm ${alertVariantClasses[variant]}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <p className="text-text">{children}</p>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Progress (bar + ring), always paired with a text label                  */
/* ---------------------------------------------------------------------- */

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercentage = true,
}: {
  value: number;
  max?: number;
  label: string;
  showPercentage?: boolean;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const displayPct = Number.isInteger(pct) ? pct.toFixed(0) : pct.toFixed(1);
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-secondary">
        <span>{label}</span>
        {showPercentage && <span>{displayPct}%</span>}
      </div>
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
        className="h-2 w-full overflow-hidden rounded-full bg-slate-100"
      >
        <div className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out motion-reduce:transition-none" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ProgressRing({
  value,
  max = 100,
  label,
  size = 96,
}: {
  value: number;
  max?: number;
  label: string;
  size?: number;
}) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const radius = size / 2 - 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={size}
        height={size}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="text-slate-200"
          stroke="currentColor"
          strokeWidth={8}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="text-primary"
          stroke="currentColor"
          strokeWidth={8}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em" className="fill-text text-lg font-semibold">
          {pct}%
        </text>
      </svg>
      <span className="text-sm text-secondary">{label}</span>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Skeleton                                                                 */
/* ---------------------------------------------------------------------- */

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-sm bg-slate-200 ${className}`} />;
}

export function LoadingRegion({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Modal                                                                    */
/* ---------------------------------------------------------------------- */

export function Modal({
  isOpen,
  onClose,
  title,
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    dialogRef.current?.focus();
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="w-full max-w-md rounded-lg bg-surface p-6 shadow-subtle focus:outline-none"
      >
        <h2 id={titleId} className="text-xl font-semibold text-text">
          {title}
        </h2>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Tooltip (keyboard-focusable, not hover-only)                            */
/* ---------------------------------------------------------------------- */

export function Tooltip({ content, children }: { content: string; children: React.ReactNode }) {
  const [visible, setVisible] = useState(false);
  const tooltipId = useId();

  return (
    <span className="relative inline-flex">
      <span
        tabIndex={0}
        aria-describedby={tooltipId}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onKeyDown={(e) => e.key === "Escape" && setVisible(false)}
      >
        {children}
      </span>
      {visible && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 mb-2 w-max max-w-xs -translate-x-1/2 rounded-sm bg-text px-2 py-1 text-xs text-white"
        >
          {content}
        </span>
      )}
    </span>
  );
}
