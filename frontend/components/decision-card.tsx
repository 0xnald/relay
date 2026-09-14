"use client";

import { Check, ShieldAlert, UserCheck, X } from "lucide-react";
import { useState } from "react";
import { formatDateTime, relativeTime, shortId } from "../lib/format";
import type { DecisionRequest } from "../lib/types";
import { Button, cx, Label, Mono, StatusBadge } from "./ui";

type Props = { decision: DecisionRequest; rescueCode?: string; onResolve?: (id: string, option: string) => Promise<void>; onOpenRescue?: (rescueId: string) => void; compact?: boolean; now: number };

function isReject(option: string): boolean {
  return /reject|decline|cancel|stop/i.test(option);
}

export function DecisionCard({ decision, rescueCode, onResolve, onOpenRescue, compact = false, now }: Props) {
  const pending = decision.status === "pending";
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resolve = async (option: string) => {
    if (!onResolve) return;
    setBusy(option); setError(null);
    try { await onResolve(decision.id, option); } catch { setError("Relay could not record this decision. Try again."); } finally { setBusy(null); }
  };
  const code = rescueCode ?? shortId(decision.rescue_id);
  return (
    <article className={cx("relative overflow-hidden rounded-card border bg-surface shadow-card", pending ? "border-amber/35" : "border-line")}>
      <span className={cx("absolute inset-y-0 left-0 w-0.5", pending ? "bg-amber" : "bg-mint/50")} aria-hidden />
      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={cx("flex h-7 w-7 items-center justify-center rounded-card-sm border", pending ? "border-amber/25 bg-amber-soft text-amber" : "border-mint/25 bg-mint-soft text-mint")}>
              {pending ? <ShieldAlert size={14} strokeWidth={1.75} aria-hidden /> : <UserCheck size={14} strokeWidth={1.75} aria-hidden />}
            </span>
            <Label className={pending ? "text-amber" : "text-mint"}>{pending ? "Human decision required" : "Human decision"}</Label>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-amber/25 bg-amber-soft px-2 py-0.5 text-2xs font-medium text-amber">Red tier · human judgment</span>
            <StatusBadge status={decision.status} />
          </div>
        </div>

        <h3 className="mt-3 text-md font-semibold text-ink">{decision.issue}</h3>
        <p className="mt-1 text-sm text-ink-2">{pending ? "Relay cannot safely resolve this automatically and has paused the rescue." : `Resolved${decision.resolution ? `: ${decision.resolution}` : ""}. The workflow resumed from where it stopped.`}</p>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
          <button onClick={() => onOpenRescue?.(decision.rescue_id)} className="font-mono text-xs text-mint hover:underline" disabled={!onOpenRescue}>rescue {code}</button>
          <Mono className="text-ink-3 tnum">requested {relativeTime(decision.requested_at ?? decision.created_at, now)}</Mono>
          {decision.resolved_at && <Mono className="text-ink-3 tnum">resolved {formatDateTime(decision.resolved_at)}</Mono>}
        </div>

        {!compact && (
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <EvidenceList title="Evidence available" items={decision.known_evidence} tone="neutral" />
            <EvidenceList title="Missing evidence" items={decision.missing_evidence} tone="amber" />
            <EvidenceList title="Relay already tried" items={decision.actions_tried} tone="neutral" />
          </div>
        )}

        {!compact && (
          <div className="mt-5 rounded-card-sm border border-line bg-elevated/60 p-3">
            <Label>Why Relay stopped</Label>
            <p className="mt-1 text-sm text-ink-2">Continuing with missing safety-relevant evidence is a red-tier action. Deterministic policy gates never let the model decide food safety, so a person chooses among the permitted options.</p>
          </div>
        )}

        {pending && decision.allowed_options.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2">
            {decision.allowed_options.map((option) => (
              <Button key={option} variant={isReject(option) ? "danger" : "amber"} icon={isReject(option) ? X : Check} disabled={busy !== null || !onResolve} onClick={() => void resolve(option)}>
                {busy === option ? "Recording…" : option.replace(/^\w/, (c) => c.toUpperCase())}
              </Button>
            ))}
          </div>
        )}
        {!pending && decision.allowed_options.length > 0 && !compact && (
          <p className="mt-4 text-xs text-ink-3">Permitted options were: {decision.allowed_options.join(" · ")}</p>
        )}
        {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      </div>
    </article>
  );
}

function EvidenceList({ title, items, tone }: { title: string; items: string[]; tone: "neutral" | "amber" }) {
  return (
    <div>
      <Label className={tone === "amber" ? "text-amber" : undefined}>{title}</Label>
      {items.length ? (
        <ul className="mt-1.5 space-y-1">
          {items.map((item) => <li key={item} className={cx("flex items-start gap-2 text-sm", tone === "amber" ? "text-ink" : "text-ink-2")}><span className={cx("mt-2 h-1 w-1 shrink-0 rounded-full", tone === "amber" ? "bg-amber" : "bg-ink-3")} aria-hidden />{item}</li>)}
        </ul>
      ) : <p className="mt-1.5 text-sm text-ink-3">None recorded</p>}
    </div>
  );
}
