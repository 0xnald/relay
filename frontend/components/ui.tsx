"use client";

import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Inbox, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { label as humanize, toneFor, type Tone } from "../lib/status";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* ---------- Status ---------- */

const badgeTone: Record<Tone, string> = {
  green: "border-mint/25 bg-mint-soft text-mint",
  amber: "border-amber/25 bg-amber-soft text-amber",
  neutral: "border-line bg-elevated text-ink-2",
  danger: "border-danger/25 bg-danger-soft text-danger"
};

const dotTone: Record<Tone, string> = { green: "bg-mint", amber: "bg-amber", neutral: "bg-ink-3", danger: "bg-danger" };

export function StatusBadge({ status, tone, size = "sm", className }: { status: string; tone?: Tone; size?: "sm" | "md"; className?: string }) {
  const resolved = tone ?? toneFor(status);
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-medium", size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm", badgeTone[resolved], className)}>
      <span className={cx("h-1.5 w-1.5 rounded-full", dotTone[resolved])} aria-hidden />
      {humanize(status)}
    </span>
  );
}

export function StatusDot({ tone, pulse = false, className }: { tone: Tone; pulse?: boolean; className?: string }) {
  return <span className={cx("inline-block h-2 w-2 rounded-full", dotTone[tone], pulse && "motion-safe:animate-pulse-dot", className)} aria-hidden />;
}

/* ---------- Typography ---------- */

export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx("text-2xs font-medium uppercase tracking-[0.08em] text-ink-3", className)}>{children}</span>;
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx("font-mono text-xs text-ink-2", className)}>{children}</span>;
}

export function SectionHeader({ title, description, action, count, className }: { title: string; description?: string; action?: ReactNode; count?: number; className?: string }) {
  return (
    <div className={cx("mb-4 flex flex-wrap items-end justify-between gap-3", className)}>
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
          {title}
          {typeof count === "number" && <span className="rounded-full border border-line bg-elevated px-2 py-0.5 font-mono text-xs font-normal text-ink-2 tnum">{count}</span>}
        </h2>
        {description && <p className="mt-1 max-w-2xl text-sm text-ink-2">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function PageTitle({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold text-ink">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-md text-ink-2">{description}</p>}
      </div>
      {action}
    </div>
  );
}

/* ---------- Surfaces ---------- */

export function Panel({ title, description, action, children, className, padded = true, tone }: { title?: string; description?: string; action?: ReactNode; children: ReactNode; className?: string; padded?: boolean; tone?: "mint" | "amber" }) {
  return (
    <section className={cx("rounded-card border bg-surface shadow-card", tone === "mint" ? "border-mint/25" : tone === "amber" ? "border-amber/30" : "border-line", className)}>
      {(title || action) && (
        <header className={cx("flex items-start justify-between gap-3 border-b border-line/70 px-5 py-4")}>
          <div>
            {title && <h3 className="text-md font-semibold text-ink">{title}</h3>}
            {description && <p className="mt-0.5 text-sm text-ink-2">{description}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={cx(padded && "p-5")}>{children}</div>
    </section>
  );
}

export function KeyValue({ items, className }: { items: Array<{ label: string; value: ReactNode; mono?: boolean }>; className?: string }) {
  return (
    <dl className={cx("grid gap-x-6 gap-y-3", className)}>
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt><Label>{item.label}</Label></dt>
          <dd className={cx("mt-1 truncate text-sm text-ink", item.mono && "font-mono text-xs")}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ---------- Metric ---------- */

export function MetricCard({ label, value, note, icon: Icon, tone = "neutral", loading = false }: { label: string; value: number | string | null | undefined; note?: string; icon: LucideIcon; tone?: Tone; loading?: boolean }) {
  const accent = tone === "green" ? "text-mint bg-mint-soft border-mint/20" : tone === "amber" ? "text-amber bg-amber-soft border-amber/20" : "text-ink-2 bg-elevated border-line";
  return (
    <div className="group rounded-card border border-line bg-surface p-5 shadow-card transition-shadow duration-base hover:shadow-card-hover">
      <div className="flex items-start justify-between gap-3">
        <Label>{label}</Label>
        <span className={cx("flex h-8 w-8 items-center justify-center rounded-card-sm border", accent)}><Icon size={16} strokeWidth={1.75} aria-hidden /></span>
      </div>
      {loading ? (
        <div className="relay-skeleton mt-3 h-9 w-16" />
      ) : (
        <p className="mt-2 text-3xl font-bold text-ink tnum transition-opacity duration-base">{value ?? "—"}</p>
      )}
      {note && <p className="mt-1.5 text-xs text-ink-3">{note}</p>}
    </div>
  );
}

/* ---------- Buttons ---------- */

type ButtonProps = { children: ReactNode; onClick?: () => void; disabled?: boolean; variant?: "primary" | "secondary" | "ghost" | "amber" | "danger"; size?: "sm" | "md" | "lg"; icon?: LucideIcon; className?: string; type?: "button" | "submit"; title?: string; "aria-label"?: string };

export function Button({ children, onClick, disabled, variant = "secondary", size = "md", icon: Icon, className, type = "button", title, ...rest }: ButtonProps) {
  const base = "inline-flex items-center justify-center gap-2 rounded-card-sm font-semibold transition-colors duration-fast disabled:opacity-50";
  const sizes = { sm: "h-8 px-3 text-xs", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-md" }[size];
  const variants = {
    primary: "bg-mint text-bg hover:bg-mint/90",
    secondary: "border border-line bg-elevated text-ink hover:border-ink-3 hover:bg-elevated/80",
    ghost: "text-ink-2 hover:bg-elevated hover:text-ink",
    amber: "bg-amber text-bg hover:bg-amber/90",
    danger: "border border-danger/40 bg-transparent text-danger hover:bg-danger-soft"
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title} aria-label={rest["aria-label"]} className={cx(base, sizes, variants, className)}>
      {Icon && <Icon size={size === "sm" ? 14 : 16} strokeWidth={1.75} aria-hidden />}
      {children}
    </button>
  );
}

/* ---------- Loading / empty / error ---------- */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("relay-skeleton", className)} aria-hidden />;
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-card border border-line bg-surface p-5" aria-busy>
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-5 w-2/3" />
      {Array.from({ length: lines }).map((_, index) => <Skeleton key={index} className={cx("mt-3 h-3", index % 2 ? "w-1/2" : "w-5/6")} />)}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, body, action }: { icon?: LucideIcon; title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="relay-grid-bg flex flex-col items-center rounded-card border border-dashed border-line bg-surface px-6 py-12 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-card-sm border border-line bg-elevated text-ink-2"><Icon size={18} strokeWidth={1.75} aria-hidden /></span>
      <h3 className="mt-4 text-md font-semibold text-ink">{title}</h3>
      {body && <p className="mt-1.5 max-w-sm text-sm text-ink-2">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorCard({ title = "Relay API is unavailable", message, onRetry, offline = false }: { title?: string; message?: string; onRetry?: () => void; offline?: boolean }) {
  const Icon = offline ? WifiOff : AlertTriangle;
  return (
    <div role="alert" className="flex flex-wrap items-start gap-4 rounded-card border border-danger/30 bg-danger-soft p-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-card-sm border border-danger/30 text-danger"><Icon size={16} strokeWidth={1.75} aria-hidden /></span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink">{title}</p>
        {message && <p className="mt-0.5 text-sm text-ink-2">{message}</p>}
      </div>
      {onRetry && <Button size="sm" variant="secondary" icon={RefreshCw} onClick={onRetry}>Retry</Button>}
    </div>
  );
}

export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="group/tip relative inline-flex">
      {children}
      <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-max max-w-[220px] -translate-x-1/2 rounded-card-sm border border-line bg-elevated px-2.5 py-1.5 text-xs text-ink-2 opacity-0 shadow-card transition-opacity duration-fast group-hover/tip:opacity-100 group-focus-within/tip:opacity-100">{text}</span>
    </span>
  );
}

export function Divider({ className }: { className?: string }) {
  return <hr className={cx("border-0 border-t border-line/70", className)} />;
}
