"use client";

import { ArrowRight, Clock, Package, Truck, Users } from "lucide-react";
import { formatDateTime, formatQuantity, relativeTime } from "../lib/format";
import { isTerminalFailure, JOURNEY, journeyIndex, label, toneFor } from "../lib/status";
import type { Rescue } from "../lib/types";
import { cx, Label, Mono, Skeleton, StatusBadge } from "./ui";

/** Slim state progress: completed stages mint, current strongest, future muted. */
export function JourneyBar({ status, className }: { status: string; className?: string }) {
  const current = journeyIndex(status);
  const failed = isTerminalFailure(status);
  const done = status === "completed";
  return (
    <div className={cx("flex items-center gap-1", className)} role="img" aria-label={`Journey stage ${current + 1} of ${JOURNEY.length}: ${JOURNEY[current].title}`}>
      {JOURNEY.map((stage, index) => (
        <span key={stage.key} title={stage.title} className={cx("h-1 flex-1 rounded-full transition-colors duration-base", failed ? "bg-danger/40" : index < current || done ? "bg-mint/55" : index === current ? "bg-mint" : "bg-line")} />
      ))}
    </div>
  );
}

export function RescueCard({ rescue, onOpen, now }: { rescue: Rescue; onOpen: (rescue: Rescue) => void; now: number }) {
  const tone = toneFor(rescue.status);
  const destination = rescue.recipients.length ? rescue.recipients.join(", ") : "Not yet matched";
  const driver = rescue.drivers.length ? rescue.drivers.join(", ") : "Not yet assigned";
  const foodParts = rescue.food_summary.split(", ").map((part) => part.replace(/^(\d+)\.\d+/, "$1"));
  const active = rescue.status !== "completed" && !isTerminalFailure(rescue.status);
  return (
    <article className="group rounded-card border border-line bg-surface p-5 shadow-card transition-all duration-base hover:-translate-y-px hover:border-ink-3/60 hover:shadow-card-hover motion-safe:animate-rise">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Mono className="text-ink-3">{rescue.short_code}</Mono>
            <StatusBadge status={rescue.status} tone={tone} />
            {rescue.exception_count > 0 && (
              <span className={cx("rounded-full border px-2 py-0.5 text-2xs font-medium tracking-normal", active ? "border-amber/25 bg-amber-soft text-amber" : "border-line bg-elevated text-ink-2")}>
                {rescue.exception_count} exception{rescue.exception_count === 1 ? "" : "s"}{active ? " · in recovery" : " · recovered"}
              </span>
            )}
          </div>
          <h3 className="mt-2 flex items-center gap-2 text-md font-semibold text-ink">
            <span className="truncate">{rescue.donor}</span>
            <ArrowRight size={14} className="shrink-0 text-ink-3" aria-hidden />
            <span className="truncate text-ink-2">{destination}</span>
          </h3>
        </div>
        <button onClick={() => onOpen(rescue)} className="inline-flex h-8 items-center gap-1.5 rounded-card-sm border border-line bg-elevated px-3 text-xs font-semibold text-ink transition-colors duration-fast hover:border-ink-3 group-hover:border-mint/40 group-hover:text-mint">
          Open <ArrowRight size={13} aria-hidden />
        </button>
      </div>

      <JourneyBar status={rescue.status} className="mt-4" />
      <div className="mt-1.5 flex justify-between">
        <Label>{label(JOURNEY[journeyIndex(rescue.status)].title)}</Label>
        <Label className="normal-case tracking-normal">updated {relativeTime(rescue.updated_at, now)}</Label>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
        <Fact icon={Package} label="Quantity" value={foodParts.length ? foodParts.join(" · ") : `${formatQuantity(rescue.food_quantity)} units`} />
        <Fact icon={Clock} label="Pickup by" value={formatDateTime(rescue.pickup_deadline)} />
        <Fact icon={Users} label="Destination" value={destination} />
        <Fact icon={Truck} label="Driver" value={driver} />
      </dl>
    </article>
  );
}

function Fact({ icon: Icon, label: text, value }: { icon: typeof Package; label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1.5"><Icon size={12} className="text-ink-3" aria-hidden /><Label>{text}</Label></dt>
      <dd className="mt-1 truncate text-sm text-ink" title={value}>{value}</dd>
    </div>
  );
}

export function RescueCardSkeleton() {
  return (
    <div className="rounded-card border border-line bg-surface p-5" aria-busy>
      <div className="flex items-center gap-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-5 w-20 rounded-full" /></div>
      <Skeleton className="mt-3 h-5 w-1/2" />
      <Skeleton className="mt-4 h-1 w-full" />
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index}><Skeleton className="h-3 w-12" /><Skeleton className="mt-2 h-4 w-3/4" /></div>)}</div>
    </div>
  );
}
