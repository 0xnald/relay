"use client";

import { ArrowRight, Bot, CheckCircle2, Database, Play, RotateCcw, Truck, UserCheck, Users } from "lucide-react";
import { humanizeExceptionType, humanizeStrategy, label } from "../../lib/status";
import type { HeroSummary } from "../../lib/types";
import type { NameResolver } from "../exception-card";
import { Button, cx, ErrorCard, Label, Mono, Panel, StatusBadge } from "../ui";

type Props = { busy: boolean; result: HeroSummary | null; error: string | null; onRun: () => void; onOpenRescue: (id: string) => void; resolveName: NameResolver };

const PREVIEW: Array<{ title: string; sub?: string; tone: "neutral" | "green" | "amber" }> = [
  { title: "Market Square", sub: "donor", tone: "neutral" },
  { title: "36 prepared meals + 12 bakery items", sub: "structured intake · deterministic policy check", tone: "neutral" },
  { title: "Harbor Community Kitchen", sub: "initial recipient · refrigerated driver", tone: "neutral" },
  { title: "Refrigerator failure", sub: "exception detected", tone: "amber" },
  { title: "Relay replans", sub: "bakery preserved · meals released · driver replaced", tone: "green" },
  { title: "Riverside Shelter", sub: "human decision on missing evidence · verified delivery", tone: "green" }
];

function names(change: string, resolve: NameResolver): string {
  return change.split("->").map((id) => resolve(id.trim()) ?? id.trim()).join(" → ");
}

export function DemoView({ busy, result, error, onRun, onOpenRescue, resolveName }: Props) {
  return (
    <div className="space-y-8">
      <section className="relay-grid-bg rounded-card-lg border border-line bg-surface p-6 shadow-card md:p-8">
        <Label>Controlled rescue scenario</Label>
        <h1 className="mt-2 text-3xl font-bold text-ink">Run a synthetic food-rescue operation through the real Relay system.</h1>
        <div className="mt-4 grid gap-3 text-sm text-ink-2 md:grid-cols-2">
          <p className="flex items-start gap-2"><Users size={15} className="mt-1 shrink-0 text-amber" aria-hidden />The organizations and people are synthetic.</p>
          <p className="flex items-start gap-2"><Database size={15} className="mt-1 shrink-0 text-mint" aria-hidden />The workflow execution, API calls, database writes, autonomous recovery, and state transitions are real.</p>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
        <Panel title="Scenario preview" description="What the run will do, in order.">
          <ol className="space-y-1">
            {PREVIEW.map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className={cx("flex h-6 w-6 items-center justify-center rounded-full border font-mono text-2xs", step.tone === "green" ? "border-mint/40 bg-mint-soft text-mint" : step.tone === "amber" ? "border-amber/40 bg-amber-soft text-amber" : "border-line bg-elevated text-ink-2")}>{index + 1}</span>
                  {index < PREVIEW.length - 1 && <span className="my-1 h-5 w-px bg-line" aria-hidden />}
                </div>
                <div className="pb-2">
                  <p className={cx("text-sm font-semibold", step.tone === "green" ? "text-mint" : step.tone === "amber" ? "text-amber" : "text-ink")}>{step.title}</p>
                  {step.sub && <p className="text-xs text-ink-3">{step.sub}</p>}
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-5 border-t border-line/70 pt-5">
            <Button variant="primary" size="lg" icon={Play} onClick={onRun} disabled={busy} className="w-full sm:w-auto">{busy ? "Running real workflow…" : "Run hero scenario"}</Button>
            <p className="mt-2 text-xs text-ink-3">Seeds the synthetic network, then runs intake, matching, two autonomous recoveries, one human decision, and verification against PostgreSQL. Usually completes in a few seconds.</p>
          </div>
        </Panel>

        <div className="space-y-4">
          {error && <ErrorCard title="The hero workflow could not run" message={error} onRetry={onRun} />}
          {busy && (
            <Panel tone="mint">
              <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-card-sm border border-mint/25 bg-mint-soft text-mint"><Bot size={16} className="motion-safe:animate-pulse-dot" aria-hidden /></span><div><p className="text-md font-semibold text-ink">Relay is coordinating…</p><p className="text-sm text-ink-2">Observing events, reasoning, acting through authorization, verifying evidence.</p></div></div>
            </Panel>
          )}
          {result ? <Summary result={result} resolveName={resolveName} onOpenRescue={onOpenRescue} /> : !busy && (
            <Panel title="Result" description="The persisted outcome appears here after a run.">
              <p className="text-sm text-ink-3">No run in this session yet. Existing rescues are on the Overview.</p>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function Summary({ result, resolveName, onOpenRescue }: { result: HeroSummary; resolveName: NameResolver; onOpenRescue: (id: string) => void }) {
  const completed = result.final_rescue_status === "completed";
  const recovered = result.exceptions.filter((item) => item.endsWith(":recovered")).length;
  return (
    <Panel tone={completed ? "mint" : "amber"} title="Run complete" description={`Rescue ${result.rescue_id.split("-")[0].toUpperCase()} · trace ${result.trace_ids.join(", ")}`} action={<StatusBadge status={result.final_rescue_status} size="md" />}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat icon={CheckCircle2} label="Delivery" value={result.delivery_verified ? "Verified" : "Unverified"} tone={result.delivery_verified ? "green" : "amber"} />
        <Stat icon={RotateCcw} label="Exceptions recovered" value={`${recovered} / ${result.exceptions.length}`} tone="green" />
        <Stat icon={UserCheck} label="Human interventions" value={String(result.human_decisions.length)} tone="amber" />
      </div>
      <dl className="mt-5 space-y-3 text-sm">
        {result.recipient_changes.map((change) => <Row key={change} icon={Users} label="Recipient reassignment" value={names(change, resolveName)} />)}
        {result.driver_changes.map((change) => <Row key={change} icon={Truck} label="Driver replacement" value={names(change, resolveName)} />)}
        {result.recoveries.map((item) => { const [strategy, ok] = item.split(":"); return <Row key={item} icon={Bot} label="Recovery" value={`${humanizeStrategy(strategy)} · ${ok === "True" ? "succeeded" : "failed"}`} />; })}
        {result.exceptions.map((item) => { const [type, status] = item.split(":"); return <Row key={item} icon={RotateCcw} label="Exception" value={`${humanizeExceptionType(type)} · ${label(status)}`} />; })}
      </dl>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line/70 pt-4">
        <Mono className="text-ink-3">{result.autonomous_actions.length} recorded autonomous actions</Mono>
        <Button variant="secondary" icon={ArrowRight} onClick={() => onOpenRescue(result.rescue_id)}>Open rescue</Button>
      </div>
    </Panel>
  );
}

function Stat({ icon: Icon, label: text, value, tone }: { icon: typeof CheckCircle2; label: string; value: string; tone: "green" | "amber" }) {
  return (
    <div className="rounded-card-sm border border-line bg-elevated/60 p-3">
      <div className="flex items-center gap-1.5"><Icon size={12} className={tone === "green" ? "text-mint" : "text-amber"} aria-hidden /><Label>{text}</Label></div>
      <p className={cx("mt-1 text-lg font-bold tnum", tone === "green" ? "text-mint" : "text-amber")}>{value}</p>
    </div>
  );
}

function Row({ icon: Icon, label: text, value }: { icon: typeof CheckCircle2; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <Icon size={14} className="mt-1 shrink-0 text-ink-3" aria-hidden />
      <div className="min-w-0"><dt><Label>{text}</Label></dt><dd className="mt-0.5 text-ink">{value}</dd></div>
    </div>
  );
}
