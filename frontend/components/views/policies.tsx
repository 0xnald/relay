"use client";

import { ArrowDown, Bot, ScrollText, ShieldCheck, UserCheck, type LucideIcon } from "lucide-react";
import { cx, Label, PageTitle, Panel, StatusDot } from "../ui";

const FLOW: Array<{ icon: LucideIcon; title: string; body: string; tone: "purple" | "neutral" | "green" | "amber" }> = [
  { icon: Bot, title: "AI interprets", body: "Strands agents extract facts from untrusted text, flag missing evidence and contradictions, and propose bounded actions from a fixed menu.", tone: "neutral" },
  { icon: ScrollText, title: "Policies constrain", body: "Deterministic completeness, eligibility, feasibility, and handling gates decide what is even possible. Amber actions need an explicit active policy.", tone: "neutral" },
  { icon: ShieldCheck, title: "Authorized actions execute", body: "AuthorizedActionService classifies every proposal. Green runs autonomously through audited tools; nothing bypasses the state machine.", tone: "green" },
  { icon: UserCheck, title: "Human judgment handles ambiguity", body: "Red conditions and ambiguous safety evidence pause the rescue and create a Decision Card. The workflow resumes when a person decides.", tone: "amber" }
];

const TIERS = [
  { tier: "Green", tone: "green" as const, behavior: "Executes autonomously when normal preconditions pass.", examples: ["Search for an alternate eligible recipient", "Search for a replacement driver", "Send operational status updates", "Request missing, non-sensitive information"] },
  { tier: "Amber", tone: "amber" as const, behavior: "Executes only when an active policy explicitly permits the action.", examples: ["Substitute a recipient", "Split a rescue or allocation", "Change an assigned driver", "Extend a pickup window"] },
  { tier: "Red", tone: "danger" as const, behavior: "Never executes without a human decision.", examples: ["Override handling requirements", "Continue with missing safety evidence", "Resolve conflicting policies", "Any food-safety determination"] }
];

export function PoliciesView() {
  return (
    <div className="space-y-8">
      <PageTitle title="Policies" description="Relay's safety control center. Authority is classified in deterministic code, not in a prompt." />

      <section className="relay-grid-bg rounded-card-lg border border-mint/25 bg-surface p-6 shadow-card md:p-8">
        <Label className="text-mint">Governing rule</Label>
        <h2 className="mt-2 text-2xl font-bold text-ink">The LLM never decides food safety.</h2>
        <p className="mt-2 max-w-2xl text-md text-ink-2">Agents interpret and propose. Deterministic services validate evidence, time windows, storage constraints, authorization, and lifecycle transitions. Output that asserts food is safe is rejected fail-closed before it reaches any workflow.</p>
      </section>

      <section>
        <ol className="grid gap-3 lg:grid-cols-4">
          {FLOW.map((step, index) => {
            const Icon = step.icon;
            return (
              <li key={step.title} className="relative">
                <div className={cx("h-full rounded-card border bg-surface p-5 shadow-card", step.tone === "green" ? "border-mint/25" : step.tone === "amber" ? "border-amber/30" : "border-line")}>
                  <div className="flex items-center justify-between">
                    <span className={cx("flex h-8 w-8 items-center justify-center rounded-card-sm border", step.tone === "green" ? "border-mint/25 bg-mint-soft text-mint" : step.tone === "amber" ? "border-amber/25 bg-amber-soft text-amber" : "border-line bg-elevated text-ink-2")}><Icon size={16} strokeWidth={1.75} aria-hidden /></span>
                    <span className="font-mono text-2xs text-ink-3">0{index + 1}</span>
                  </div>
                  <h3 className="mt-4 text-md font-semibold text-ink">{step.title}</h3>
                  <p className="mt-1.5 text-sm text-ink-2">{step.body}</p>
                </div>
                {index < FLOW.length - 1 && <ArrowDown size={16} className="mx-auto my-1 text-ink-3 lg:absolute lg:-right-3.5 lg:top-1/2 lg:my-0 lg:-translate-y-1/2 lg:-rotate-90" aria-hidden />}
              </li>
            );
          })}
        </ol>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {TIERS.map((tier) => (
          <Panel key={tier.tier} tone={tier.tone === "green" ? "mint" : tier.tone === "amber" ? "amber" : undefined} title={tier.tier} action={<StatusDot tone={tier.tone} className="mt-2" />}>
            <p className="text-sm text-ink">{tier.behavior}</p>
            <ul className="mt-4 space-y-1.5">
              {tier.examples.map((example) => <li key={example} className="flex items-start gap-2 text-sm text-ink-2"><span className={cx("mt-2 h-1 w-1 shrink-0 rounded-full", tier.tone === "green" ? "bg-mint" : tier.tone === "amber" ? "bg-amber" : "bg-danger")} aria-hidden />{example}</li>)}
            </ul>
          </Panel>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Panel title="Fail-closed guards">
          <ul className="space-y-2 text-sm text-ink-2">
            <li>Intake output containing an authoritative safety phrase is discarded entirely.</li>
            <li>Donor text is data inside delimiters; instructions inside it are ignored.</li>
            <li>Every tool call passes authorization; a tool cannot bypass policy.</li>
            <li>Rescue state changes are versioned, audited, and idempotent.</li>
          </ul>
        </Panel>
        <Panel title="What reaches a person">
          <ul className="space-y-2 text-sm text-ink-2">
            <li>Missing or contradictory safety-relevant evidence.</li>
            <li>Red-tier actions such as overriding handling requirements.</li>
            <li>Conflicting active policies.</li>
            <li>Nothing else — routine declines, cancellations, and storage loss are recovered autonomously.</li>
          </ul>
        </Panel>
      </section>
    </div>
  );
}
