"use client";

import { CheckCircle2, GitBranch, PlayCircle, RotateCcw, Truck, UserCheck } from "lucide-react";
import { greeting } from "../../lib/format";
import { isTerminalFailure } from "../../lib/status";
import type { AgentRuntimeStatus, Dashboard, Rescue, RescueDetail } from "../../lib/types";
import { RescueCard, RescueCardSkeleton } from "../rescue-card";
import { condense, Timeline } from "../timeline";
import { Button, cx, EmptyState, Label, MetricCard, Mono, Panel, SectionHeader, Skeleton, StatusDot } from "../ui";

type Props = {
  dashboard: Dashboard | null;
  loading: boolean;
  online: boolean;
  runtime: AgentRuntimeStatus | null;
  latestDetail: RescueDetail | null;
  latestLoading: boolean;
  now: number;
  onOpen: (rescue: Rescue) => void;
  onRunDemo: () => void;
  onViewAll: () => void;
  onViewDecisions: () => void;
  demoBusy: boolean;
};

export function OverviewView({ dashboard, loading, online, runtime, latestDetail, latestLoading, now, onOpen, onRunDemo, onViewAll, onViewDecisions, demoBusy }: Props) {
  const metrics = dashboard?.metrics ?? {};
  const rescues = dashboard?.rescues ?? [];
  const active = rescues.filter((item) => item.status !== "completed" && !isTerminalFailure(item.status));
  const recent = rescues.filter((item) => !active.includes(item)).slice(0, 3);
  const pending = (dashboard?.decisions ?? []).filter((item) => item.status === "pending").length;
  const showSkeleton = loading && !dashboard;

  return (
    <div className="space-y-8">
      {/* Hero strip */}
      <section className="relay-grid-bg overflow-hidden rounded-card-lg border border-line bg-surface shadow-card">
        <div className="grid gap-6 p-6 md:p-8 xl:grid-cols-[1.4fr_1fr]">
          <div>
            <Label>{greeting(new Date(now))}</Label>
            <h1 className="mt-2 text-3xl font-bold text-ink">Rescue operations</h1>
            <p className="mt-3 max-w-xl text-md text-ink-2">Relay is coordinating your active food-rescue network. Routine failures are recovered autonomously; only ambiguous evidence reaches a person.</p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="primary" icon={PlayCircle} onClick={onRunDemo} disabled={demoBusy}>{demoBusy ? "Running scenario…" : "Run hero scenario"}</Button>
              <Button variant="secondary" onClick={onViewAll}>All rescues</Button>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 self-center sm:grid-cols-3 xl:gap-4">
            <HeroStat label="System" value={online ? "Nominal" : "Offline"} tone={online ? "green" : "danger"} sub={runtime ? runtime.provider : "—"} />
            <HeroStat label="Active rescues" value={showSkeleton ? null : String(active.length)} tone="neutral" sub={`${rescues.length} total`} />
            <HeroStat label="Pending decisions" value={showSkeleton ? null : String(pending)} tone={pending ? "amber" : "neutral"} sub={pending ? "awaiting judgment" : "none waiting"} onClick={onViewDecisions} />
          </div>
        </div>
      </section>

      {/* Metrics */}
      <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <MetricCard label="Active rescues" value={showSkeleton ? null : metrics.active_rescues ?? 0} note={`${metrics.at_risk_rescues ?? 0} at risk`} icon={Truck} tone="neutral" loading={showSkeleton} />
        <MetricCard label="Recoveries" value={showSkeleton ? null : metrics.recoveries ?? 0} note="autonomous, no human paged" icon={RotateCcw} tone="green" loading={showSkeleton} />
        <MetricCard label="Human interventions" value={showSkeleton ? null : metrics.human_interventions ?? 0} note="red-tier decisions" icon={UserCheck} tone="amber" loading={showSkeleton} />
        <MetricCard label="Completed today" value={showSkeleton ? null : metrics.completed_today ?? 0} note={`${metrics.food_rescued ?? 0} units rescued`} icon={CheckCircle2} tone="green" loading={showSkeleton} />
      </section>

      <div className="grid gap-8 xl:grid-cols-[1.6fr_1fr]">
        {/* Active operations */}
        <section>
          <SectionHeader title="Active operations" count={active.length} description="Rescues in flight, ordered by latest activity." action={<Button size="sm" variant="ghost" onClick={onViewAll}>View all</Button>} />
          {showSkeleton ? (
            <div className="space-y-4"><RescueCardSkeleton /><RescueCardSkeleton /></div>
          ) : active.length ? (
            <div className="space-y-4">{active.map((rescue) => <RescueCard key={rescue.id} rescue={rescue} onOpen={onOpen} now={now} />)}</div>
          ) : (
            <EmptyState icon={Truck} title="No rescues in flight" body={rescues.length ? "Every rescue on the board has reached a terminal state." : "Run the hero scenario to put a synthetic rescue through the real Relay system."} action={!rescues.length ? <Button variant="primary" icon={PlayCircle} onClick={onRunDemo} disabled={demoBusy}>Run hero scenario</Button> : undefined} />
          )}
          {recent.length > 0 && (
            <div className="mt-8">
              <SectionHeader title="Recently completed" count={recent.length} />
              <div className="space-y-4">{recent.map((rescue) => <RescueCard key={rescue.id} rescue={rescue} onOpen={onOpen} now={now} />)}</div>
            </div>
          )}
        </section>

        {/* Operational activity */}
        <section>
          <SectionHeader title="Operational activity" description={latestDetail ? `Latest rescue · ${latestDetail.rescue.short_code}` : "Latest rescue timeline"} />
          <Panel padded>
            {latestLoading && !latestDetail ? (
              <Timeline events={[]} loading />
            ) : latestDetail ? (
              <>
                <Timeline events={condense(latestDetail.timeline).slice().reverse()} compact limit={9} />
                <button onClick={() => onOpen(latestDetail.rescue)} className="mt-1 text-xs font-semibold text-mint hover:underline">Open full timeline →</button>
              </>
            ) : (
              <EmptyState icon={GitBranch} title="No activity yet" body="Events appear here as soon as a rescue is observed." />
            )}
          </Panel>
          <div className="mt-4 rounded-card border border-line bg-surface p-4">
            <Label>Legend</Label>
            <ul className="mt-2 space-y-1.5 text-xs text-ink-2">
              <li className="flex items-center gap-2"><StatusDot tone="green" />Autonomous action or verification</li>
              <li className="flex items-center gap-2"><StatusDot tone="amber" />Human judgment or detected exception</li>
              <li className="flex items-center gap-2"><StatusDot tone="neutral" />Informational state change</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}

function HeroStat({ label, value, sub, tone, onClick }: { label: string; value: string | null; sub: string; tone: "green" | "amber" | "neutral" | "danger"; onClick?: () => void }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} className={cx("rounded-card border border-line bg-elevated/70 p-4 text-left", onClick && "transition-colors duration-fast hover:border-ink-3")}>
      <Label>{label}</Label>
      {value === null ? <Skeleton className="mt-2 h-7 w-12" /> : (
        <p className={cx("mt-1.5 flex items-center gap-2 text-xl font-bold tnum", tone === "green" ? "text-mint" : tone === "amber" ? "text-amber" : tone === "danger" ? "text-danger" : "text-ink")}>
          <StatusDot tone={tone} pulse={tone === "green"} />{value}
        </p>
      )}
      <Mono className="text-ink-3">{sub}</Mono>
    </Tag>
  );
}
