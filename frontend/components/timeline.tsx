"use client";

import { AlertTriangle, Bot, CheckCircle2, CircleDot, UserCheck, type LucideIcon } from "lucide-react";
import { formatDateTime, formatTime } from "../lib/format";
import { categorize, describeEvent, label, type EventCategory } from "../lib/status";
import type { TimelineEvent } from "../lib/types";
import { cx, EmptyState, Label as SmallLabel, Mono, Skeleton } from "./ui";

const CATEGORY: Record<EventCategory, { icon: LucideIcon; node: string; title: string }> = {
  autonomous: { icon: Bot, node: "border-mint/40 bg-mint-soft text-mint", title: "Autonomous action" },
  human: { icon: UserCheck, node: "border-amber/40 bg-amber-soft text-amber", title: "Human judgment" },
  exception: { icon: AlertTriangle, node: "border-amber/30 bg-elevated text-amber", title: "Exception detected" },
  verification: { icon: CheckCircle2, node: "border-mint/30 bg-elevated text-mint", title: "Verification" },
  state: { icon: CircleDot, node: "border-line bg-elevated text-ink-3", title: "State change" }
};

export type TimelineItem = TimelineEvent & { rescue?: string; rescueId?: string };

/** Collapses the paired `<event>` / `process_<event>` rows into one entry with the state outcome. */
export function condense(events: TimelineEvent[]): TimelineItem[] {
  const out: TimelineItem[] = [];
  for (const event of events) {
    if (event.kind.startsWith("process_") && out.length) {
      const previous = out[out.length - 1];
      if (`process_${previous.kind}` === event.kind) {
        const summary = typeof event.detail.summary === "string" ? event.detail.summary : null;
        out[out.length - 1] = { ...previous, detail: { ...previous.detail, outcome: summary ?? previous.detail.outcome } };
        continue;
      }
    }
    out.push(event);
  }
  return out;
}

export function TimelineNode({ category, size = "md" }: { category: EventCategory; size?: "sm" | "md" }) {
  const meta = CATEGORY[category];
  const Icon = meta.icon;
  return (
    <span title={meta.title} className={cx("flex shrink-0 items-center justify-center rounded-full border", meta.node, size === "sm" ? "h-6 w-6" : "h-8 w-8")}>
      <Icon size={size === "sm" ? 12 : 14} strokeWidth={1.75} aria-hidden />
    </span>
  );
}

type TimelineProps = { events: TimelineItem[]; loading?: boolean; compact?: boolean; limit?: number; showRescue?: boolean; onOpenRescue?: (id: string) => void; emptyTitle?: string; emptyBody?: string };

export function Timeline({ events, loading = false, compact = false, limit, showRescue = false, onOpenRescue, emptyTitle = "No activity yet", emptyBody = "Events appear here as Relay observes, acts, and verifies." }: TimelineProps) {
  if (loading) {
    return (
      <ol className="space-y-4" aria-busy>
        {Array.from({ length: 5 }).map((_, index) => (
          <li key={index} className="flex gap-3"><Skeleton className="h-8 w-8 rounded-full" /><div className="flex-1"><Skeleton className="h-3.5 w-1/3" /><Skeleton className="mt-2 h-3 w-2/3" /></div></li>
        ))}
      </ol>
    );
  }
  const items = limit ? events.slice(0, limit) : events;
  if (!items.length) return <EmptyState title={emptyTitle} body={emptyBody} />;
  return (
    <ol className="relative">
      {items.map((event, index) => {
        const category = categorize(event.kind);
        const outcome = typeof event.detail.outcome === "string" ? event.detail.outcome : null;
        const last = index === items.length - 1;
        return (
          <li key={`${event.kind}-${event.at}-${index}`} className={cx("relative flex gap-3 motion-safe:animate-rise", compact ? "pb-4" : "pb-5", !last && "before:absolute before:left-4 before:top-8 before:h-[calc(100%-2rem)] before:w-px before:bg-line")} style={{ animationDelay: `${Math.min(index, 12) * 25}ms` }}>
            <TimelineNode category={category} />
            <div className="min-w-0 flex-1 pt-0.5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <p className="text-sm font-semibold text-ink">{label(event.kind)}</p>
                <Mono className="text-ink-3 tnum">{compact ? formatTime(event.at) : formatDateTime(event.at)}</Mono>
              </div>
              <p className="mt-0.5 text-sm text-ink-2">{describeEvent(event.kind, event.detail)}</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                <SmallLabel className="normal-case tracking-normal">by <span className="font-mono text-ink-2">{event.actor}</span></SmallLabel>
                {outcome && <SmallLabel className="normal-case tracking-normal">→ {outcome.replace(/^Rescue state is /, "state: ")}</SmallLabel>}
                {showRescue && event.rescue && (
                  <button onClick={() => event.rescueId && onOpenRescue?.(event.rescueId)} className="font-mono text-2xs tracking-normal text-mint hover:underline">{event.rescue}</button>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
