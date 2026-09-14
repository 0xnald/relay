# Relay demo video script

Hard limit: **under 5:00**. Target **4:40–4:55**. One take per section, screen recording at
1440×900 with the public command center, plus brief cuts to the repo, the AWS console, and the
architecture diagram. Narration is written to be read at a natural pace (~140 wpm).

Before recording:

- Open https://relay-command-center-three.vercel.app on **Overview** with at least one completed
  rescue already on the board (run the demo once beforehand). Runtime label shows "Local".
- Open a second tab on **Demo Control**.
- Have `docs/architecture.svg`, `backend/app/services/action_execution.py`,
  `backend/app/agents/factory.py`, the AWS console AgentCore runtime page for `relay_intake`, and
  the CloudWatch log group `/aws/bedrock-agentcore/runtimes/RelayIntake_relay_intake-hT8Z8OBxX6-DEFAULT`
  ready in tabs.
- Hide bookmarks and notifications.

---

## 0:00–0:20 — Problem

**On screen:** Overview page, cursor idle. Then a slow zoom on the amber "Demo environment"
banner.

> Food rescue already has donation platforms and volunteer platforms. The harder problem is what
> happens *after* a rescue starts and reality changes. A fridge fails. A driver cancels. Nobody
> wrote down when the food was cooked. All of that lands on one coordinator, while the food's
> clock is running.
>
> This is Relay. It doesn't help rescuers coordinate. It coordinates.

## 0:20–1:00 — Intake and initial plan

**On screen:** Switch to the **Demo Control** tab. Click **Seed and run hero scenario**. The
rescue detail opens (~3 s). Scroll slowly through "Food and handling" and "Assignments and
recovery".

> Market Square is donating 36 prepared chicken meals and 12 bakery items, with a three-hour
> pickup window. Relay's Strands Intake Agent turns the donor's text into structured facts —
> quantities, handling categories, what's known and what's missing.
>
> From there, everything consequential is deterministic. Eligibility, feasibility, and scoring
> pick Harbor Community Kitchen for both items, and a refrigerated driver for the meals. Every
> action you'll see went through Relay's authorization service before it ran — green actions
> execute, amber actions need an explicit policy, red actions need a person.

## 1:00–2:15 — Autonomous recovery

**On screen:** In "Assignments and recovery": point to `36 meals → Harbor Community Kitchen ·
Cancelled`, then `36 meals → Riverside Shelter · Reserved`, then `12 items → Harbor · Reserved`.
Scroll the timeline to "Recipient Capability Lost → Recovery Started → Substitute Recipient →
Recovery Completed".

> Now reality changes. Harbor loses its cold storage. Relay releases only the food that needs it —
> the 36 prepared meals — and re-matches them to Riverside Shelter. The bakery items stay at
> Harbor. That's a substitution, an amber action, permitted by the active policy. Nobody was
> paged.

**On screen:** Point to `Driver assignment: Maya · Cancelled` and the replacement driver rows.
Scroll to "Driver Cancelled → Search Replacement Driver → Recovery Completed".

> Then the driver cancels. Relay searches for a replacement with a refrigerated vehicle and
> assigns one. Again, no human intervention — this is exactly the routine operational failure an
> autonomous coordinator should absorb.
>
> Two failures, two recoveries, zero interruptions. And every step is in the timeline with the
> actor that took it.

## 2:15–3:10 — Human judgment

**On screen:** Scroll to "Missing Information" in the timeline, then open the **Decisions** view
to show the card "Prepared-food preparation time evidence is missing" with status Resolved. Cut to
the "Human Decision Received … approve documented exception" timeline entry.

> Here's the part that matters most. The preparation-time evidence for the prepared meals is
> missing. Relay does not invent an answer, and the model is never asked whether the food is safe.
> That's a red condition, so Relay pauses the rescue, creates a Decision Card, and waits.
>
> A coordinator reviews it and approves a documented exception. The workflow resumes from exactly
> where it stopped. This is the whole design: autonomous on routine failures, and a human in the
> loop only when human judgment is what's actually needed.

## 3:10–3:45 — Verification

**On screen:** Scroll the timeline through "Pickup Confirmed → In transit → Delivery Confirmed →
Verifying → Completed". Land on the "Delivery receipt — ✓ Delivery verified" panel. Then cut back
to **Overview** showing the completed rescue, "3 resolved" risk, and the metrics.

> Pickup is confirmed. Delivery is confirmed. Relay verifies the evidence, marks the rescue
> completed, and issues a verified receipt. Back on the overview you can see the recovered
> exceptions and the one human intervention it took.
>
> Everything you just saw is persisted state from real services against PostgreSQL — the UI
> doesn't fake anything.

## 3:45–4:25 — Technical proof

**On screen (≈10 s each):**
1. `docs/architecture.svg` — hover the three colours.
2. `backend/app/agents/factory.py` — the three Strands agents.
3. `backend/app/services/action_execution.py` — `AuthorizedActionService`.
4. AWS console: AgentCore runtime `relay_intake`, status READY, Python 3.12 CodeZip.
5. CloudWatch log group with the per-session `Invocation completed successfully` and the one
   `Invocation failed … AgentInterpretationFailure` entry.

> Under the hood: blue is deterministic — the rescue engine, the state machine, the authorization
> service. Purple is bounded LLM reasoning — three Strands agents on Amazon Bedrock. Amber is human
> judgment.
>
> The Intake Agent is also deployed on its own to Amazon Bedrock AgentCore Runtime, as a narrow
> package with no tools and no state. We verified it remotely with a normal donation, a donation
> with missing evidence, and a prompt-injection attempt — and when the model echoed a donor's
> "it is safe" claim, Relay's guard rejected the whole response. That's the failure you can see in
> CloudWatch. Fail closed, by design.

## 4:25–4:50 — Close

**On screen:** Back to the command center Overview. Fade to the title card with the repo URL and
demo URL.

> Food rescue doesn't only have a matching problem. It has a coordination problem.
>
> Relay doesn't help food rescuers coordinate. Relay coordinates — and asks humans only when human
> judgment matters.

---

## Timing check

| Section | Target | Words | ≈ seconds at 140 wpm |
| --- | --- | --- | --- |
| Problem | 0:20 | 58 | 25 |
| Intake + plan | 0:40 | 95 | 41 |
| Autonomous recovery | 1:15 | 145 | 62 |
| Human judgment | 0:55 | 113 | 48 |
| Verification | 0:35 | 71 | 30 |
| Technical proof | 0:40 | 118 | 51 |
| Close | 0:25 | 31 | 13 + title card |
| **Total** | **4:50** | | **≈4:35 narration + pauses** |

If the recording runs long, cut the last sentence of "Intake and initial plan" and the
"Everything you just saw…" line in Verification first.
