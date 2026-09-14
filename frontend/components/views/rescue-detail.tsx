"use client";

import { ArrowLeft, Check, CheckCircle2, Clock, MapPin, Package, Snowflake, Thermometer, Truck, Users } from "lucide-react";
import { formatDateTime, formatQuantity } from "../../lib/format";
import { isTerminalFailure, JOURNEY, journeyIndex, label, toneFor } from "../../lib/status";
import type { RescueDetail } from "../../lib/types";
import { DecisionCard } from "../decision-card";
import { ExceptionCard, type NameResolver } from "../exception-card";
import { condense, Timeline } from "../timeline";
import { Button, cx, EmptyState, KeyValue, Label, Mono, Panel, Skeleton, StatusBadge } from "../ui";

type Props = { detail: RescueDetail | null; loading: boolean; onBack: () => void; resolveName: NameResolver; onResolveDecision: (id: string, option: string) => Promise<void>; now: number };

export function Journey({ status }: { status: string }) {
  const current = journeyIndex(status);
  const done = status === "completed";
  const failed = isTerminalFailure(status);
  return (
    <ol className="grid grid-cols-4 gap-2 md:grid-cols-8" aria-label="Rescue journey">
      {JOURNEY.map((stage, index) => {
        const complete = done || index < current;
        const active = !done && index === current;
        return (
          <li key={stage.key} className="min-w-0">
            <div className={cx("h-1 rounded-full transition-colors duration-base", failed ? "bg-danger/40" : complete ? "bg-mint/55" : active ? "bg-mint" : "bg-line")} />
            <p className={cx("mt-2 flex items-center gap-1 truncate text-xs", active ? "font-semibold text-ink" : complete ? "text-mint/90" : "text-ink-3")}>
              {complete && <Check size={11} aria-hidden />}{stage.title}
            </p>
            {active && <Mono className="text-ink-3">{label(status)}</Mono>}
          </li>
        );
      })}
    </ol>
  );
}

export function RescueDetailView({ detail, loading, onBack, resolveName, onResolveDecision, now }: Props) {
  if (loading || !detail) {
    return (
      <div className="space-y-6" aria-busy>
        <Skeleton className="h-4 w-32" />
        <div className="rounded-card border border-line bg-surface p-6"><Skeleton className="h-3 w-24" /><Skeleton className="mt-3 h-8 w-1/2" /><Skeleton className="mt-6 h-1 w-full" /></div>
        <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]"><Skeleton className="h-96" /><Skeleton className="h-96" /></div>
      </div>
    );
  }
  const { rescue } = detail;
  const primary = detail.food_items[0];
  const activeAllocations = detail.allocations.filter((item) => item.status !== "cancelled");
  const activeAssignments = detail.assignments.filter((item) => item.status !== "cancelled");
  const recoveriesByException = new Map(detail.recoveries.map((item) => [item.exception_id, item]));
  const autonomous = detail.exceptions.filter((item) => recoveriesByException.has(item.id));
  const other = detail.exceptions.filter((item) => !recoveriesByException.has(item.id));
  const pendingDecision = detail.decisions.find((item) => item.status === "pending");
  const timeline = condense(detail.timeline);

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-2 transition-colors duration-fast hover:text-mint"><ArrowLeft size={14} aria-hidden />Back to rescues</button>

      {/* Header */}
      <section className="relay-grid-bg rounded-card-lg border border-line bg-surface p-6 shadow-card md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Mono className="text-ink-3">RESCUE</Mono>
              <span className="font-mono text-sm text-ink">{rescue.short_code}</span>
              <StatusBadge status={rescue.status} size="md" />
              {detail.receipt.verified && <span className="inline-flex items-center gap-1 text-xs font-semibold text-mint"><CheckCircle2 size={13} aria-hidden />Delivery verified</span>}
            </div>
            <h1 className="mt-2 text-3xl font-bold text-ink">{detail.donor}</h1>
            <p className="mt-1 text-sm text-ink-2">{rescue.recipients.length ? `→ ${rescue.recipients.join(", ")}` : "Destination not yet matched"}</p>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
            <div><dt><Label>Pickup by</Label></dt><dd className="mt-1 flex items-center gap-1.5 text-sm text-ink"><Clock size={13} className="text-ink-3" aria-hidden />{formatDateTime(rescue.pickup_deadline)}</dd></div>
            <div><dt><Label>Primary quantity</Label></dt><dd className="mt-1 flex items-center gap-1.5 text-sm text-ink"><Package size={13} className="text-ink-3" aria-hidden />{primary ? `${formatQuantity(primary.quantity)} ${primary.unit} ${primary.name}` : "—"}</dd></div>
            <div><dt><Label>Trace</Label></dt><dd className="mt-1 font-mono text-xs text-ink-2">{detail.trace_id ?? "—"}</dd></div>
          </dl>
        </div>
        <div className="mt-8"><Journey status={rescue.status} /></div>
      </section>

      {pendingDecision && <DecisionCard decision={pendingDecision} rescueCode={rescue.short_code} onResolve={onResolveDecision} now={now} />}

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        {/* Left column */}
        <div className="space-y-6">
          {(autonomous.length > 0 || other.length > 0) && (
            <section>
              <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold text-ink">Exceptions and recovery</h2><Mono className="text-ink-3">{detail.exceptions.length} detected</Mono></div>
              <div className="grid gap-4 md:grid-cols-2">
                {autonomous.map((exception) => <ExceptionCard key={exception.id} exception={exception} recovery={recoveriesByException.get(exception.id)} allocations={detail.allocations} assignments={detail.assignments} timeline={detail.timeline} resolveName={resolveName} />)}
              </div>
              {other.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {other.map((exception) => (
                    <li key={exception.id} className="flex flex-wrap items-center justify-between gap-2 rounded-card-sm border border-line bg-surface px-4 py-3">
                      <span className="text-sm text-ink">{label(exception.exception_type)} <span className="text-ink-3">· handled through human review</span></span>
                      <StatusBadge status={exception.status} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <Panel title="Rescue journey" description="Immutable event timeline with the actor for every step.">
            <Timeline events={timeline} />
          </Panel>

          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="Allocations" description="Where each food item is reserved.">
              {detail.allocations.length ? (
                <ul className="space-y-2">
                  {detail.allocations.map((allocation) => (
                    <li key={allocation.id} className={cx("flex items-center justify-between gap-3 rounded-card-sm border px-3 py-2.5", allocation.status === "cancelled" ? "border-line/60 bg-transparent text-ink-3" : "border-line bg-elevated/60")}>
                      <span className="min-w-0 truncate text-sm"><span className="font-semibold tnum">{formatQuantity(allocation.quantity)} {allocation.unit}</span> <span className="text-ink-3">→</span> {allocation.recipient}</span>
                      <StatusBadge status={allocation.status} tone={allocation.status === "cancelled" ? "neutral" : toneFor(allocation.status)} />
                    </li>
                  ))}
                </ul>
              ) : <EmptyState icon={Users} title="No allocations yet" />}
            </Panel>
            <Panel title="Assignments" description="Driver assignments, including replacements.">
              {detail.assignments.length ? (
                <ul className="space-y-2">
                  {detail.assignments.map((assignment) => (
                    <li key={assignment.id} className={cx("flex items-center justify-between gap-3 rounded-card-sm border px-3 py-2.5", assignment.status === "cancelled" ? "border-line/60 text-ink-3" : "border-line bg-elevated/60")}>
                      <span className="flex items-center gap-2 text-sm"><Truck size={13} className="text-ink-3" aria-hidden />{assignment.driver}<Mono className="text-ink-3">{formatDateTime(assignment.created_at)}</Mono></span>
                      <StatusBadge status={assignment.status} tone={assignment.status === "cancelled" ? "neutral" : toneFor(assignment.status)} />
                    </li>
                  ))}
                </ul>
              ) : <EmptyState icon={Truck} title="No driver assigned yet" />}
            </Panel>
          </div>
        </div>

        {/* Right column */}
        <aside className="space-y-6">
          <Panel title="Current state">
            <KeyValue className="grid-cols-2" items={[
              { label: "Status", value: <StatusBadge status={rescue.status} /> },
              { label: "Stage", value: JOURNEY[journeyIndex(rescue.status)].title },
              { label: "Route", value: detail.route.source },
              { label: "Feasibility", value: detail.route.pickup_feasible ? "Pickup feasible" : "Re-check required" }
            ]} />
          </Panel>

          <Panel title="Policy status">
            <ul className="space-y-2 text-sm">
              <li className="flex items-center justify-between"><span className="text-ink-2">Autonomous recoveries</span><span className="font-mono text-mint tnum">{detail.recoveries.filter((item) => item.succeeded).length}</span></li>
              <li className="flex items-center justify-between"><span className="text-ink-2">Human decisions</span><span className="font-mono text-amber tnum">{detail.decisions.length}</span></li>
              <li className="flex items-center justify-between"><span className="text-ink-2">Open exceptions</span><span className="font-mono text-ink tnum">{detail.exceptions.filter((item) => !["recovered", "resolved"].includes(item.status)).length}</span></li>
            </ul>
            <p className="mt-3 border-t border-line/70 pt-3 text-xs text-ink-3">Green actions ran autonomously; amber actions were policy-permitted; red conditions waited for a person.</p>
          </Panel>

          <Panel title="Recipient">
            {activeAllocations.length ? activeAllocations.map((allocation) => (
              <div key={allocation.id} className="flex items-start gap-2 py-1 text-sm"><Users size={14} className="mt-0.5 text-ink-3" aria-hidden /><span><span className="font-semibold text-ink">{allocation.recipient}</span><br /><span className="text-ink-2">{formatQuantity(allocation.quantity)} {allocation.unit}</span></span></div>
            )) : <p className="text-sm text-ink-3">Not yet matched</p>}
          </Panel>

          <Panel title="Driver">
            {activeAssignments.length ? activeAssignments.map((assignment) => (
              <div key={assignment.id} className="flex items-center gap-2 py-1 text-sm"><Truck size={14} className="text-ink-3" aria-hidden /><span className="font-semibold text-ink">{assignment.driver}</span><StatusBadge status={assignment.status} /></div>
            )) : <p className="text-sm text-ink-3">Not yet assigned</p>}
          </Panel>

          <Panel title="Food and handling">
            <ul className="space-y-2">
              {detail.food_items.map((item) => (
                <li key={item.name} className="rounded-card-sm border border-line bg-elevated/60 px-3 py-2.5 text-sm">
                  <p className="font-semibold text-ink"><span className="tnum">{formatQuantity(item.quantity)} {item.unit}</span> {item.name}</p>
                  <p className="mt-1 flex items-center gap-1.5 text-xs text-ink-2">{item.requires_refrigeration ? <Snowflake size={12} className="text-mint" aria-hidden /> : <Thermometer size={12} className="text-ink-3" aria-hidden />}{label(item.handling_category)} · {item.requires_refrigeration ? "cold chain required" : "ambient handling"}</p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Verification" tone={detail.receipt.verified ? "mint" : undefined}>
            <div className="flex items-start gap-3">
              <span className={cx("flex h-10 w-10 items-center justify-center rounded-card-sm border", detail.receipt.verified ? "border-mint/25 bg-mint-soft text-mint" : "border-line bg-elevated text-ink-3")}><CheckCircle2 size={18} strokeWidth={1.75} aria-hidden /></span>
              <div>
                <p className="text-md font-semibold text-ink">{detail.receipt.verified ? "Delivery verified" : "Verification pending"}</p>
                <p className="text-sm text-ink-2">{detail.receipt.verified ? `Receipt recorded ${formatDateTime(detail.receipt.completed_at)}` : "Pickup and delivery evidence not yet complete."}</p>
              </div>
            </div>
          </Panel>

          {detail.decisions.filter((item) => item.status !== "pending").map((decision) => (
            <DecisionCard key={decision.id} decision={decision} rescueCode={rescue.short_code} compact now={now} />
          ))}

          <div className="rounded-card border border-line bg-surface p-4">
            <Label>Location</Label>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-2"><MapPin size={13} className="text-ink-3" aria-hidden />Route source: {detail.route.source}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onBack} icon={ArrowLeft}>Back</Button>
        </aside>
      </div>
    </div>
  );
}
