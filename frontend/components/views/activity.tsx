"use client";

import { Activity } from "lucide-react";
import { useMemo, useState } from "react";
import { categorize, type EventCategory } from "../../lib/status";
import type { Dashboard, RescueDetail } from "../../lib/types";
import { condense, Timeline, type TimelineItem } from "../timeline";
import { cx, EmptyState, ErrorCard, PageTitle, Panel } from "../ui";

type Props = { dashboard: Dashboard | null; details: Record<string, RescueDetail>; loading: boolean; error: string | null; onRetry: () => void; onOpenRescue: (rescueId: string) => void };

const FILTERS: Array<{ key: EventCategory | "all"; label: string }> = [
  { key: "all", label: "All" },
  { key: "autonomous", label: "Autonomous" },
  { key: "human", label: "Human" },
  { key: "exception", label: "Exceptions" },
  { key: "verification", label: "Verification" },
  { key: "state", label: "State" }
];

export function ActivityView({ dashboard, details, loading, error, onRetry, onOpenRescue }: Props) {
  const [filter, setFilter] = useState<EventCategory | "all">("all");
  const events = useMemo<TimelineItem[]>(() => {
    const merged: TimelineItem[] = [];
    for (const rescue of dashboard?.rescues ?? []) {
      const detail = details[rescue.id];
      if (!detail) continue;
      for (const event of condense(detail.timeline)) merged.push({ ...event, rescue: rescue.short_code, rescueId: rescue.id });
    }
    return merged.sort((a, b) => b.at.localeCompare(a.at));
  }, [dashboard, details]);
  const visible = filter === "all" ? events : events.filter((event) => categorize(event.kind) === filter);
  const counts = useMemo(() => {
    const out: Record<string, number> = { all: events.length };
    for (const event of events) out[categorize(event.kind)] = (out[categorize(event.kind)] ?? 0) + 1;
    return out;
  }, [events]);
  const covered = Object.keys(details).length;
  return (
    <div>
      <PageTitle title="Activity" description={`Operational event stream across the ${covered} most recent rescue${covered === 1 ? "" : "s"}, newest first. Every entry is an immutable persisted event.`} action={
        <div role="tablist" aria-label="Filter events" className="flex flex-wrap rounded-card-sm border border-line bg-surface p-1">
          {FILTERS.map((item) => (
            <button key={item.key} role="tab" aria-selected={filter === item.key} onClick={() => setFilter(item.key)} className={cx("rounded-[8px] px-3 py-1.5 text-xs font-semibold transition-colors duration-fast", filter === item.key ? "bg-elevated text-ink" : "text-ink-2 hover:text-ink")}>
              {item.label} <span className="ml-1 font-mono text-ink-3 tnum">{counts[item.key] ?? 0}</span>
            </button>
          ))}
        </div>
      } />
      {error && <div className="mb-6"><ErrorCard message={error} onRetry={onRetry} /></div>}
      <Panel>
        {loading && !events.length ? <Timeline events={[]} loading /> : events.length ? (
          <Timeline events={visible} showRescue onOpenRescue={onOpenRescue} emptyTitle="No events in this category" emptyBody="Try another filter." />
        ) : (
          <EmptyState icon={Activity} title="No activity yet" body="Run the hero scenario to produce real events and agent audit records." />
        )}
      </Panel>
    </div>
  );
}
