"use client";

import { Inbox, UserCheck } from "lucide-react";
import type { Dashboard } from "../../lib/types";
import { DecisionCard } from "../decision-card";
import { CardSkeleton, EmptyState, PageTitle, SectionHeader } from "../ui";

type Props = { dashboard: Dashboard | null; loading: boolean; now: number; onResolve: (id: string, option: string) => Promise<void>; onOpenRescue: (rescueId: string) => void };

export function DecisionsView({ dashboard, loading, now, onResolve, onOpenRescue }: Props) {
  const decisions = dashboard?.decisions ?? [];
  const codes = new Map((dashboard?.rescues ?? []).map((rescue) => [rescue.id, rescue.short_code]));
  const pending = decisions.filter((item) => item.status === "pending");
  const resolved = decisions.filter((item) => item.status !== "pending").sort((a, b) => (b.resolved_at ?? b.updated_at ?? "").localeCompare(a.resolved_at ?? a.updated_at ?? ""));
  return (
    <div className="space-y-10">
      <PageTitle title="Decisions" description="Only evidence gaps and policy-sensitive actions reach people. Everything else Relay handles inside deterministic authority." />
      <section>
        <SectionHeader title="Needs attention" count={pending.length} description="Rescues paused until a person chooses a permitted option." />
        {loading && !dashboard ? <CardSkeleton lines={4} /> : pending.length ? (
          <div className="space-y-4">{pending.map((decision) => <DecisionCard key={decision.id} decision={decision} rescueCode={codes.get(decision.rescue_id)} onResolve={onResolve} onOpenRescue={onOpenRescue} now={now} />)}</div>
        ) : <EmptyState icon={Inbox} title="Nothing waiting on a person" body="Relay is operating inside its deterministic authority. When evidence is ambiguous, a Decision Card appears here." />}
      </section>
      <section>
        <SectionHeader title="Recently resolved" count={resolved.length} description="Human decisions already recorded in the rescue timeline." />
        {loading && !dashboard ? <CardSkeleton /> : resolved.length ? (
          <div className="grid gap-4 xl:grid-cols-2">{resolved.map((decision) => <DecisionCard key={decision.id} decision={decision} rescueCode={codes.get(decision.rescue_id)} onOpenRescue={onOpenRescue} compact now={now} />)}</div>
        ) : <EmptyState icon={UserCheck} title="No resolved decisions yet" body="Run the hero scenario to see a documented evidence exception resolved by a coordinator." />}
      </section>
    </div>
  );
}
