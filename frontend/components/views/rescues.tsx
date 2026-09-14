"use client";

import { Truck } from "lucide-react";
import { useState } from "react";
import { isTerminalFailure } from "../../lib/status";
import type { Dashboard, Rescue } from "../../lib/types";
import { RescueCard, RescueCardSkeleton } from "../rescue-card";
import { cx, EmptyState, PageTitle } from "../ui";

type Filter = "all" | "active" | "completed";

export function RescuesView({ dashboard, loading, now, onOpen }: { dashboard: Dashboard | null; loading: boolean; now: number; onOpen: (rescue: Rescue) => void }) {
  const [filter, setFilter] = useState<Filter>("all");
  const rescues = dashboard?.rescues ?? [];
  const visible = rescues.filter((item) => filter === "all" ? true : filter === "completed" ? item.status === "completed" : item.status !== "completed" && !isTerminalFailure(item.status));
  const counts: Record<Filter, number> = {
    all: rescues.length,
    active: rescues.filter((item) => item.status !== "completed" && !isTerminalFailure(item.status)).length,
    completed: rescues.filter((item) => item.status === "completed").length
  };
  return (
    <div>
      <PageTitle title="Rescues" description="Operational cases ordered by their latest activity. Every card reads persisted state." action={
        <div role="tablist" aria-label="Filter rescues" className="flex rounded-card-sm border border-line bg-surface p-1">
          {(["all", "active", "completed"] as Filter[]).map((key) => (
            <button key={key} role="tab" aria-selected={filter === key} onClick={() => setFilter(key)} className={cx("rounded-[8px] px-3 py-1.5 text-xs font-semibold capitalize transition-colors duration-fast", filter === key ? "bg-elevated text-ink" : "text-ink-2 hover:text-ink")}>
              {key} <span className="ml-1 font-mono text-ink-3 tnum">{counts[key]}</span>
            </button>
          ))}
        </div>
      } />
      {loading && !dashboard ? (
        <div className="space-y-4"><RescueCardSkeleton /><RescueCardSkeleton /><RescueCardSkeleton /></div>
      ) : visible.length ? (
        <div className="space-y-4">{visible.map((rescue) => <RescueCard key={rescue.id} rescue={rescue} onOpen={onOpen} now={now} />)}</div>
      ) : (
        <EmptyState icon={Truck} title={rescues.length ? "Nothing matches this filter" : "No operational rescues yet"} body={rescues.length ? "Try another filter." : "Run the hero scenario from the Demo page to populate the command center with a real persisted rescue."} />
      )}
    </div>
  );
}
