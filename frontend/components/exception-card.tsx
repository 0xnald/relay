"use client";

import { AlertTriangle, Bot, Check, Circle } from "lucide-react";
import { formatDateTime, formatQuantity } from "../lib/format";
import { humanizeExceptionType, humanizeStrategy, label } from "../lib/status";
import type { Allocation, Assignment, OperationalException, Recovery, TimelineEvent } from "../lib/types";
import { cx, Label, Mono, StatusBadge } from "./ui";

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

export type NameResolver = (id: string) => string | undefined;

type Derived = {
  subject: string | null;
  narrative: string;
  steps: Array<{ text: string; done: boolean }>;
};

/** Everything shown on the card is derived from persisted records; nothing is assumed. */
export function deriveRecovery(exception: OperationalException, recovery: Recovery | undefined, allocations: Allocation[], assignments: Assignment[], timeline: TimelineEvent[], resolve: NameResolver): Derived {
  const context = exception.context ?? {};
  const affectedAllocation = typeof context.allocation_id === "string" ? allocations.find((item) => item.id === context.allocation_id) : undefined;
  const cancelledAssignment = assignments.find((item) => item.status === "cancelled");
  const subject = affectedAllocation?.recipient ?? (exception.exception_type.startsWith("driver") ? cancelledAssignment?.driver ?? null : null);

  const sentences: string[] = [];
  if (affectedAllocation) {
    const moved = allocations.find((item) => item.id !== affectedAllocation.id && item.status !== "cancelled" && item.quantity === affectedAllocation.quantity && item.recipient !== affectedAllocation.recipient);
    const preserved = allocations.filter((item) => item.id !== affectedAllocation.id && item.status !== "cancelled" && item.recipient === affectedAllocation.recipient);
    if (preserved.length) sentences.push(`Relay preserved ${preserved.map((item) => `${formatQuantity(item.quantity)} ${item.unit}`).join(" and ")} at ${affectedAllocation.recipient}`);
    if (moved) sentences.push(`${sentences.length ? "and " : "Relay "}reassigned ${formatQuantity(affectedAllocation.quantity)} ${affectedAllocation.unit} to ${moved.recipient}.`);
  }
  // Driver replacements come straight from the persisted recovery outcome ("Driver changed from X to Y").
  if (!sentences.length && recovery) sentences.push(`Relay: ${recovery.outcome_summary.replace(UUID, (id) => resolve(id) ?? id)}`);
  if (!sentences.length && exception.exception_type.startsWith("driver") && cancelledAssignment) sentences.push(`Relay searched for a replacement for ${cancelledAssignment.driver}.`);
  const narrative = sentences.join(" ").replace(/\s+\./g, ".");

  const kinds = new Set(timeline.map((event) => event.kind));
  const actionKind = exception.exception_type.startsWith("driver") ? "search_replacement_driver" : "substitute_recipient";
  const steps = [
    { text: `${humanizeExceptionType(exception.exception_type)} detected`, done: true },
    { text: recovery ? `Strategy: ${humanizeStrategy(recovery.strategy)}` : "Recovery strategy selected", done: Boolean(recovery) || kinds.has("recovery_started") },
    { text: "Authorized action recorded", done: kinds.has(actionKind) },
    { text: exception.exception_type.startsWith("driver") ? "Assignment updated" : "Allocation updated", done: exception.exception_type.startsWith("driver") ? assignments.some((item) => item.status !== "cancelled") : allocations.some((item) => item.status !== "cancelled") },
    { text: "Timeline recorded", done: kinds.has("recovery_completed") }
  ];
  return { subject, narrative, steps };
}

type Props = { exception: OperationalException; recovery?: Recovery; allocations: Allocation[]; assignments: Assignment[]; timeline: TimelineEvent[]; resolveName: NameResolver };

export function ExceptionCard({ exception, recovery, allocations, assignments, timeline, resolveName }: Props) {
  const derived = deriveRecovery(exception, recovery, allocations, assignments, timeline, resolveName);
  const recovered = exception.status === "recovered" && recovery?.succeeded !== false;
  return (
    <article className={cx("relative overflow-hidden rounded-card border bg-surface p-5 shadow-card", recovered ? "border-mint/25" : "border-amber/30")}>
      <span className={cx("absolute inset-y-0 left-0 w-0.5", recovered ? "bg-mint" : "bg-amber")} aria-hidden />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={cx("flex h-7 w-7 items-center justify-center rounded-card-sm border", recovered ? "border-mint/25 bg-mint-soft text-mint" : "border-amber/25 bg-amber-soft text-amber")}>
            {recovered ? <Bot size={14} strokeWidth={1.75} aria-hidden /> : <AlertTriangle size={14} strokeWidth={1.75} aria-hidden />}
          </span>
          <Label className={recovered ? "text-mint" : "text-amber"}>{recovered ? "Autonomous recovery" : "Exception"}</Label>
        </div>
        <StatusBadge status={exception.status} />
      </div>
      <h3 className="mt-3 text-md font-semibold text-ink">{humanizeExceptionType(exception.exception_type)}</h3>
      {derived.subject && <p className="text-sm text-ink-2">{derived.subject}</p>}
      {derived.narrative && <p className="mt-3 text-sm leading-relaxed text-ink">{derived.narrative}</p>}
      <ul className="mt-4 space-y-1.5">
        {derived.steps.map((step) => (
          <li key={step.text} className="flex items-center gap-2 text-sm">
            {step.done ? <Check size={14} className="text-mint" aria-hidden /> : <Circle size={12} className="text-ink-3" aria-hidden />}
            <span className={step.done ? "text-ink-2" : "text-ink-3"}>{step.text}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line/70 pt-3">
        <span className={cx("text-xs font-semibold", recovered ? "text-mint" : "text-amber")}>{recovered ? "Recovered automatically" : label(exception.status)}</span>
        <Mono className="text-ink-3">severity {exception.severity} · {formatDateTime(exception.detected_at)}</Mono>
      </div>
    </article>
  );
}
