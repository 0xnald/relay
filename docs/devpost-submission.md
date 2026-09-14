# Devpost submission — Relay

Track: **Good Neighbor Agents** (AWS Agents for Humans Hackathon).
Public demo: https://relay-command-center-three.vercel.app · Source: https://github.com/0xnald/relay

## Project name

Relay

## Tagline

Autonomous coordination for food rescue — Relay coordinates, and asks humans only when human
judgment matters.

## Short description

Relay is an autonomous coordination layer for food rescue operations. It observes each rescue,
reasons about operational constraints with bounded Strands agents, acts within deterministic
authority, verifies outcomes, recovers from routine failures like storage loss and driver
cancellations on its own, and creates a Decision Card for a person only when evidence or policy is
genuinely ambiguous. The LLM never decides food safety.

## Inspiration

Food rescue already has donation boards and volunteer sign-ups. What it doesn't have is anyone
whose job is the two hours *after* a rescue starts, when reality changes. A recipient's
refrigerator fails. The driver cancels. Nobody wrote down when the chicken was cooked. Each of those
lands on a coordinator's phone at the exact moment the food's clock is running — and the
coordinator is usually a volunteer with three other rescues in flight.

We wanted to build the thing that carries a rescue through that mess: not another matching
marketplace, but an agent that keeps coordinating while the plan falls apart, and that knows the
difference between a routine failure it should fix and a judgment call it must hand to a person.

## What it does

Relay runs one loop for every rescue: **OBSERVE → REASON → ACT → VERIFY → RECOVER → ESCALATE**.

- It ingests typed, idempotent events from donors, recipients, drivers, and systems.
- A Strands **Intake Agent** turns untrusted donor text into structured facts with per-fact
  confidence, missing-information lists, and contradictions.
- A deterministic **Rescue Engine** decides eligibility, feasibility, scoring, allocation, driver
  assignment, and every lifecycle transition.
- A Strands **Coordination Agent** proposes bounded actions through six audited tools; every
  proposal passes through `AuthorizedActionService`, which classifies it **Green** (execute),
  **Amber** (only if an active policy allows it), or **Red** (a human must decide).
- When a recipient loses cold storage, Relay releases only the affected food and re-matches it.
  When a driver cancels, it finds a replacement with the right vehicle. No human is asked.
- When preparation-time evidence for prepared food is missing, Relay does not guess. It pauses the
  rescue, creates a Decision Card, and resumes when a coordinator resolves it.
- It records pickup and delivery evidence, and closes the rescue with a verified receipt and an
  immutable timeline.

The public command center runs the full hero scenario — 36 prepared chicken meals and 12 bakery
items from Market Square — against a real PostgreSQL database in about three seconds, and shows
the recipient reassignment, driver replacement, human decision, and verified completion.

## How we built it

- **Backend:** Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2, Alembic, PostgreSQL 17.
  Domain models are independent of the web framework, the database session, and the agent SDK.
  Rescue state is versioned and every transition is audited; event processing is idempotent with a
  transactional outbox.
- **Agents:** Strands Agents SDK 1.55 with Amazon Bedrock (Claude via a global inference profile).
  Three bounded agents share one factory: Intake (structured output, no tools), Coordination (six
  audited application tools, bounded proposal schema), and Exception (chooses among deterministic
  permitted recovery strategies). Lifecycle hooks record safe telemetry and never log prompts or
  reasoning.
- **Safety:** a deterministic completeness evaluator, evidence gates, and a fail-closed pattern
  guard that rejects any intake output containing an authoritative safety phrase. Donor text is
  data inside delimiters, never instructions.
- **AgentCore:** the narrow Intake Agent is packaged deterministically (24 files, no database,
  API, tools, or MCP client) and deployed to Amazon Bedrock AgentCore Runtime as a Python 3.12
  CodeZip. It was verified with real remote sessions, including prompt-injection attempts, and its
  invocations are visible in CloudWatch.
- **Frontend:** Next.js 16 operations command center on Vercel, proxying same-origin `/api/*`
  calls to the Relay API on Railway.
- **Quality:** ruff, strict mypy, 105 backend tests (unit, API, PostgreSQL integration with real
  concurrency and the hero workflow), frontend typecheck/lint/test/build, all on GitHub Actions.

## Challenges we ran into

- **Keeping the LLM out of food-safety decisions without making it useless.** The answer was a
  strict split: agents extract, flag, and propose from a fixed menu; deterministic code decides.
  The guard that rejects authoritative safety language fired for real during remote verification
  when the model echoed a donor's "it is safe" claim — exactly the fail-closed behaviour we wanted,
  and a reminder that the boundary has to live in code.
- **Making autonomy trustworthy.** Every action passes a Green/Amber/Red classification, and Amber
  actions need an explicit policy. It is easy to build an agent that does things; it is harder to
  build one whose every action is explainable after the fact.
- **A narrow AgentCore package.** Relay's backend imports FastAPI, SQLAlchemy, and a full domain
  package. Getting a clean, minimal CodeZip meant loosening import coupling so the intake path can
  load without the web or persistence layers, then validating the package in an isolated Python
  3.12 environment before deploying.
- **Least-privilege IAM the honest way.** `InvokeAgentRuntime` authorizes against both the runtime
  ARN and its `runtime-endpoint/DEFAULT` sub-resource; we learned that from two precise denials
  rather than by granting wildcards.
- **A demo that survives being clicked twice.** The first public run exposed that the hero
  scenario assumed a freshly seeded network. The fix restores the synthetic network's operational
  baseline on every run while keeping earlier rescues intact — covered by a regression test.

## Accomplishments that we're proud of

- A rescue that recovers from two operational failures on its own and stops for exactly one human
  decision — running end to end, persisted, in public.
- A deterministic safety boundary that is enforced in code, tested offline, and verified against
  the deployed AgentCore runtime with hostile input.
- Real observability: CloudWatch shows every invocation of the deployed Intake Agent, including
  the fail-closed rejection.
- Zero fabricated behaviour in the demo: the command center reads only persisted state produced by
  real services.

## What we learned

- Coordination is a state-machine problem with an LLM at the edges, not an LLM problem with a
  database at the edges.
- "Ask a human only when it matters" needs a concrete definition. Ours is: Red actions and
  ambiguous or missing safety evidence. Everything else is either autonomous or policy-gated.
- Prompt injection is best handled structurally — delimited data, bounded schemas, no tools on the
  intake path — and then verified against the real deployed runtime, not just in unit tests.
- Deploying to AgentCore is most reliable when the package is small and boring.

## What's next for Relay

- Wire the Relay API's intake endpoint to the deployed AgentCore runtime behind the existing
  execution-mode setting, with the same fail-closed guard on the response.
- Real donor, driver, and recipient channels (SMS/WhatsApp intake, driver confirmations) feeding
  the same event pipeline.
- A live routing provider in place of the static demo routes.
- Coordinator-facing explanations for every autonomous action, generated from the audit trail.
- Pilot with a local food-rescue organization on real, non-safety-critical coordination first.

## Built with

Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Strands Agents SDK, Amazon Bedrock,
Amazon Bedrock AgentCore Runtime, Amazon CloudWatch, AWS CDK, TypeScript, Next.js, React, Tailwind
CSS, Vercel, Railway, Docker, uv, pnpm, GitHub Actions.

## Submission links

- Public demo: https://relay-command-center-three.vercel.app
- Public API health: https://relay-api-production-721e.up.railway.app/health
- Repository: https://github.com/0xnald/relay
- Architecture diagram: `docs/architecture.svg`
- Demo video: see `docs/demo-script.md` (to be recorded)
