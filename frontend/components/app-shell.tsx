"use client";

import { Activity, Boxes, Gauge, GitBranch, Menu, PlayCircle, RefreshCw, ShieldCheck, Truck, X, type LucideIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { formatTime } from "../lib/format";
import type { AgentRuntimeStatus } from "../lib/types";
import { Button, cx, Label, StatusDot, Tooltip } from "./ui";

export const NAVIGATION = ["Overview", "Rescues", "Network", "Decisions", "Activity", "Policies", "Demo"] as const;
export type View = (typeof NAVIGATION)[number];

const NAV_ICONS: Record<View, LucideIcon> = {
  Overview: Gauge,
  Rescues: Truck,
  Network: Boxes,
  Decisions: GitBranch,
  Activity: Activity,
  Policies: ShieldCheck,
  Demo: PlayCircle
};

const NAV_GROUPS: Array<{ title: string; items: View[] }> = [
  { title: "Operate", items: ["Overview", "Rescues", "Network"] },
  { title: "Govern", items: ["Decisions", "Activity", "Policies"] },
  { title: "Scenario", items: ["Demo"] }
];

export function runtimeLabel(status: AgentRuntimeStatus | null): string {
  if (status?.runtime_verified) return "AgentCore verified";
  if (status?.runtime_configured) return "AgentCore configured";
  return "Local Strands";
}

export function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-7 w-7 items-center justify-center rounded-[8px] bg-mint text-bg" aria-hidden>
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12 8 4l5 8" /><path d="M5.5 12h5" /></svg>
      </span>
      <span className="text-[17px] font-bold tracking-tight text-ink">relay</span>
    </div>
  );
}

type SidebarProps = { view: View; onNavigate: (view: View) => void; runtime: AgentRuntimeStatus | null; demo: boolean; open: boolean; onClose: () => void };

export function Sidebar({ view, onNavigate, runtime, demo, open, onClose }: SidebarProps) {
  return (
    <>
      <div className={cx("fixed inset-0 z-30 bg-bg/70 backdrop-blur-[2px] transition-opacity duration-base lg:hidden", open ? "opacity-100" : "pointer-events-none opacity-0")} onClick={onClose} aria-hidden />
      <aside
        aria-label="Primary navigation"
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-line bg-surface transition-transform duration-base lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <Wordmark />
          <button onClick={onClose} className="rounded-card-sm p-1.5 text-ink-2 hover:bg-elevated lg:hidden" aria-label="Close navigation"><X size={16} /></button>
        </div>
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-4 pt-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              <Label className="px-3">{group.title}</Label>
              <ul className="mt-2 space-y-0.5">
                {group.items.map((item) => {
                  const Icon = NAV_ICONS[item];
                  const active = item === view;
                  return (
                    <li key={item}>
                      <button
                        onClick={() => { onNavigate(item); onClose(); }}
                        aria-current={active ? "page" : undefined}
                        className={cx(
                          "flex w-full items-center gap-3 rounded-card-sm px-3 py-2 text-sm font-medium transition-colors duration-fast",
                          active ? "bg-mint-soft text-mint" : "text-ink-2 hover:bg-elevated hover:text-ink"
                        )}
                      >
                        <Icon size={16} strokeWidth={1.75} className={active ? "text-mint" : "text-ink-3"} aria-hidden />
                        {item}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
        <div className="space-y-3 border-t border-line px-5 py-4">
          <div className="flex items-center justify-between">
            <Label>Environment</Label>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber"><StatusDot tone="amber" />{demo ? "Synthetic demo" : "Live"}</span>
          </div>
          <div className="flex items-center justify-between">
            <Label>Agent runtime</Label>
            <Tooltip text={runtime ? `${runtime.provider} · ${runtime.region} · mode ${runtime.execution_mode}` : "Runtime status unavailable"}>
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-2"><StatusDot tone={runtime?.runtime_verified ? "green" : "neutral"} />{runtimeLabel(runtime)}</span>
            </Tooltip>
          </div>
          <p className="font-mono text-2xs normal-case tracking-normal text-ink-3">relay command center · v0.1.0</p>
        </div>
      </aside>
    </>
  );
}

type TopbarProps = { view: View; section?: string; demo: boolean; lastRefresh: number | null; stale: boolean; online: boolean; refreshing: boolean; onRefresh: () => void; onOpenNav: () => void };

export function Topbar({ view, section, demo, lastRefresh, stale, online, refreshing, onRefresh, onOpenNav }: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-line bg-bg/85 px-4 backdrop-blur md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button onClick={onOpenNav} className="rounded-card-sm p-1.5 text-ink-2 hover:bg-elevated lg:hidden" aria-label="Open navigation"><Menu size={18} /></button>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{section ?? view}</p>
          {section && <p className="truncate text-xs text-ink-3">{view}</p>}
        </div>
      </div>
      <div className="flex items-center gap-2 md:gap-4">
        {demo && <span className="hidden items-center gap-1.5 rounded-full border border-amber/25 bg-amber-soft px-2.5 py-1 text-xs font-medium text-amber sm:inline-flex"><StatusDot tone="amber" />Synthetic data</span>}
        <span className="hidden items-center gap-2 text-xs text-ink-3 md:inline-flex">
          <StatusDot tone={online ? (stale ? "amber" : "green") : "danger"} pulse={online && !stale} />
          {online ? (stale ? "Data may be stale" : "Live") : "Disconnected"}
          {lastRefresh && <span className="font-mono tnum">· {formatTime(new Date(lastRefresh).toISOString())}</span>}
        </span>
        <Button size="sm" variant="ghost" icon={RefreshCw} onClick={onRefresh} disabled={refreshing} className={cx(refreshing && "[&>svg]:motion-safe:animate-spin")} aria-label="Refresh data">
          <span className="hidden sm:inline">Refresh</span>
        </Button>
      </div>
    </header>
  );
}

type AppShellProps = { view: View; section?: string; onNavigate: (view: View) => void; runtime: AgentRuntimeStatus | null; demo: boolean; lastRefresh: number | null; stale: boolean; online: boolean; refreshing: boolean; onRefresh: () => void; children: ReactNode };

export function AppShell({ view, section, onNavigate, runtime, demo, lastRefresh, stale, online, refreshing, onRefresh, children }: AppShellProps) {
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setNavOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);
  return (
    <div className="min-h-screen bg-bg text-ink">
      <div className="mx-auto flex max-w-[1680px]">
        <Sidebar view={view} onNavigate={onNavigate} runtime={runtime} demo={demo} open={navOpen} onClose={() => setNavOpen(false)} />
        <div className="relay-grid-bg min-w-0 flex-1">
          <Topbar view={view} section={section} demo={demo} lastRefresh={lastRefresh} stale={stale} online={online} refreshing={refreshing} onRefresh={onRefresh} onOpenNav={() => setNavOpen(true)} />
          <main className="px-4 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
