# Relay

**Food rescue doesn't only have a matching problem. It has a coordination problem.**

Relay is an autonomous coordination layer for food rescue operations. It observes rescues, reasons
about operational constraints, takes safe actions, verifies outcomes, recovers from routine
failures, and interrupts humans only when judgment is actually required.

> Relay doesn't help food rescuers coordinate. Relay coordinates — and asks humans only when human
> judgment matters.

| | |
| --- | --- |
| **Public demo** | https://relay-command-center-three.vercel.app — open **Demo Control** → *Seed and run hero scenario* |
| **Public API** | https://relay-api-production-721e.up.railway.app/health |
| **Track** | AWS Agents for Humans Hackathon — Good Neighbor Agents |
| **License** | [MIT](LICENSE) |
| **Built with** | Strands Agents SDK · Amazon Bedrock · Amazon Bedrock AgentCore Runtime · FastAPI · PostgreSQL · Next.js |

The demo environment is synthetic: organizations, drivers, metrics, and rescues are seeded demo
data, never real operations.

## The problem

Donation and volunteer platforms already exist. The harder problem is what happens *after* a rescue
starts and reality changes. A recipient's refrigerator fails. A driver cancels an hour before
pickup. Preparation-time evidence for hot food is missing. Each of these routinely lands on an
already-stretched coordinator, at exactly the moment the food's clock is running.

Relay carries a rescue through that operational work — assignment, transport, evidence, recovery,
and receipt — while keeping food-safety, policy, and consequential decisions under deterministic
or human control.

## What Relay does

Relay runs one operating loop for every rescue:

```text
OBSERVE → REASON → ACT → VERIFY → RECOVER → ESCALATE
```

- **Observe** typed, idempotent events from donors, recipients, drivers, and systems.
- **Reason** with bounded Strands agents: structured intake, coordination proposals, and recovery
  strategy selection.
- **Act** only through `AuthorizedActionService`, which classifies every proposed action before
  anything executes.
- **Verify** pickup and delivery evidence, time windows, storage constraints, and lifecycle
  transitions in deterministic code.
- **Recover** from routine failures — declines, cancellations, storage loss — with the
  deterministic rescue engine.
- **Escalate** ambiguity, missing critical evidence, and unsafe conditions to a human Decision
  Card, then resume when a person decides.

## The hero workflow

The public demo runs this scenario end to end through real services against a persisted
PostgreSQL database, in about three seconds:

1. **Intake.** Market Square donates 36 prepared chicken meals (cold chain required) and 12 bakery
   items with a three-hour pickup window.
2. **Initial plan.** Deterministic eligibility, feasibility, and scoring select Harbor Community
   Kitchen for both items and a refrigerated driver for the meals.
3. **Refrigerator failure.** Harbor loses cold storage. Relay releases only the prepared meals,
   re-matches them to Riverside Shelter, and leaves the bakery items at Harbor. No human is asked.
4. **Driver cancellation.** The assigned driver cancels. Relay searches for and assigns a
   replacement with a refrigerated vehicle. No human is asked.
5. **Missing evidence.** Preparation-time evidence for the prepared meals is missing. Relay does not
   invent an answer: it creates a Decision Card and pauses that rescue in `human_review`.
6. **Human decision.** A coordinator approves a documented exception. The workflow resumes.
7. **Verification.** Pickup and delivery are confirmed, the rescue reaches `completed`, and a
   verified receipt is recorded.

The command center shows the recipient reassignment, driver replacement, resolved decision, the
full immutable timeline, and the verified receipt.

## Autonomy model

Every proposed action is classified before execution:

| Level | Relay behavior | Examples |
| --- | --- | --- |
| **Green** | Execute autonomously | Search for an alternate recipient, replace a cancelled driver, send status updates |
| **Amber** | Execute only when an active policy explicitly allows it | Split a rescue, substitute a recipient, change an assigned driver |
| **Red** | Require a human decision | Override handling requirements, continue with missing evidence, resolve conflicting policies |

The classification lives in deterministic code, not in a prompt. See
[Autonomy and safety](docs/autonomy-and-safety.md).

## Deterministic safety boundary

**The LLM never decides food safety.**

- Agents extract facts, flag missing information and contradictions, propose bounded actions from a
  fixed menu, and choose among deterministic recovery strategies.
- Deterministic services decide everything consequential: `IntakeCompletenessEvaluator`,
  `EligibilityEngine`, `FeasibilityEngine`, `AuthorizedActionService`, the rescue state machine,
  and `HumanReviewService`.
- Intake output that contains an authoritative safety phrase ("the food is safe") is rejected
  fail-closed by a pattern guard before it reaches any workflow.
- Donor text is treated as data inside delimiters, never as instructions. Prompt-injection attempts
  to escalate authority, mark evidence verified, mutate state, or reveal reasoning were tested
  against the deployed runtime and had no effect.
- Ambiguous or missing safety evidence stops the rescue and creates a Decision Card.

## Strands Agents

Relay uses the [Strands Agents SDK](https://strandsagents.com) (`strands-agents==1.55.1`) with
Amazon Bedrock as the model provider. Three bounded agents share one factory
(`backend/app/agents/factory.py`):

| Agent | Purpose | Output | Tools |
| --- | --- | --- | --- |
| **Intake** | Extract operational facts from untrusted donor text | `DonationIntakeResult` structured output with per-fact confidence and verification flags | none |
| **Coordination** | Propose bounded rescue actions from the persisted state | `CoordinationProposal` | six audited application tools: `get_rescue`, `get_rescue_events`, `get_policy`, `evaluate_rescue_constraints`, `propose_action`, `request_information` |
| **Exception** | Select among deterministic permitted recovery strategies | `RecoveryProposal` | none |

Every tool goes through `AuthorizedActionService`; a tool call cannot bypass policy. Strands
lifecycle hooks record safe telemetry (agent name, trace ID, tool, outcome, latency) and never log
prompts, donor text, or reasoning. Tests run the agents with a deterministic model, so the full
suite is offline and repeatable. See [Relay agents and Strands architecture](docs/agents.md).

## Amazon Bedrock AgentCore

Relay's **narrow Intake Agent** is deployed to Amazon Bedrock AgentCore Runtime and verified with
real remote invocations:

- Runtime `relay_intake` (`RelayIntake_relay_intake-hT8Z8OBxX6`), `us-east-1`, Python 3.12
  CodeZip, HTTP protocol.
- The package contains only the intake modules — no database, API, tools, or MCP client. It is
  generated deterministically by `scripts/prepare_agentcore_intake_package.py`.
- Verified remotely: a normal donation returns `ready`, missing handling evidence returns
  `needs_clarification`, a hostile prompt returns `requires_human_review`, and output containing an
  authoritative safety phrase is rejected fail-closed. CloudWatch runtime logs and Transaction
  Search are verified.

AgentCore hosts **only** the Intake Agent. The rescue engine, policy gates, human review, and
persistence run in the Relay API. Details, IAM shape, and observability limits are in
[AgentCore deployment](docs/agentcore-deployment.md).

## Architecture

![Relay architecture](docs/architecture.svg)

```mermaid
flowchart TB
    subgraph UI["Command center — Next.js on Vercel"]
        CC[Overview · Rescues · Network · Decisions · Activity · Policies · Demo]
    end
    subgraph API["Relay API — FastAPI on Railway"]
        EV[Event ingestion<br/>idempotent, typed]
        RE[["Deterministic Rescue Engine<br/>eligibility · feasibility · scoring<br/>state machine · recovery"]]
        AAS[["AuthorizedActionService<br/>Green / Amber / Red"]]
        HR{{"Decision Requests<br/>human review"}}
        subgraph AG["Strands agents (LLM reasoning)"]
            IA(Intake)
            CA(Coordination + 6 audited tools)
            XA(Exception)
        end
    end
    DB[(PostgreSQL)]
    subgraph AWS["AWS us-east-1"]
        AC(["AgentCore Runtime<br/>narrow Intake Agent only"])
        BR(Amazon Bedrock<br/>Claude)
        CW[(CloudWatch logs<br/>Transaction Search)]
    end
    CC -->|same-origin /api proxy| EV
    EV --> RE
    RE --> AG
    AG --> AAS
    AAS --> RE
    AAS -.red.-> HR
    HR -->|human decides| RE
    RE --> DB
    IA -. deployed copy .-> AC
    AC --> BR
    AG --> BR
    AC --> CW
```

Solid boxes are deterministic policy and state logic; rounded nodes are LLM reasoning; the diamond
is human judgment. See [Architecture](docs/architecture.md),
[Matching and recovery](docs/matching-and-recovery.md), and
[Transactional event processing](docs/event-processing.md).

## Repository structure

```text
backend/
  app/
    api/              HTTP routes and transport concerns
    agents/           Strands agent factory, Bedrock model, prompts
    core/             settings, errors, logging, request tracing
    domain/           framework-independent entities, events, policies
    services/         deterministic matching, authorization, recovery, review
    tools/            bounded Strands tools backed by audited services
    workflows/        rescue workflow and the executable hero scenario
    repositories/     persistence boundaries and unit of work
    models/           SQLAlchemy persistence models
    schemas/          validated transport and structured-output schemas
    observability/    safe agent telemetry hooks
  agentcore_runtime.py  AgentCore entrypoint for the narrow Intake Agent
  migrations/         Alembic revisions
  tests/              deterministic unit, API, and PostgreSQL integration tests
frontend/             Next.js operations command center
agentcore-runtime/    AgentCore CLI project (config, CDK, deployed state)
scripts/              hero scenario runner, AgentCore package builder, API start script
docs/                 architecture, safety, agents, deployment, submission
Dockerfile            Relay API production image (Railway)
```

## Setup and local development

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 24 with pnpm, and PostgreSQL
(the Compose file pins the release used in CI).

```bash
git clone https://github.com/0xnald/relay.git
cd relay
cp .env.example .env
uv sync --dev
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Open http://localhost:3000 and run the hero scenario. The frontend proxies `/api/*` to the backend;
set `RELAY_API_ORIGIN` at build time to point a hosted frontend at a hosted API. Without AWS
credentials, everything except live Bedrock calls works: the hero scenario, command center, and
tests are fully deterministic.

Backend environment variables are prefixed `RELAY_` (see `.env.example`): `DATABASE_URL`,
`CORS_ORIGINS`, `ENVIRONMENT`, `LOG_LEVEL`, `AGENT_MODEL_ID`, `AWS_REGION`. Live Bedrock calls use
the normal AWS credential chain; no keys are stored in the repository.

You can also run the hero scenario without the UI:

```bash
uv run python scripts/run_hero_scenario.py
```

## Public demo deployment

- **Frontend:** Next.js on Vercel (`frontend/`), `RELAY_API_ORIGIN` set to the Railway API.
- **API + PostgreSQL:** Railway, built from the root `Dockerfile`; `scripts/start_api.sh` applies
  Alembic migrations on boot. `RELAY_ENVIRONMENT=staging` keeps the synthetic demo control
  available (it is disabled in `production`). CORS is restricted to the Vercel origins.
- **Intake Agent:** Amazon Bedrock AgentCore Runtime, `us-east-1`.

The API surface: `GET /health`, `GET /ready`, `POST /api/v1/events`, `POST /api/v1/agent/intake`,
`GET /api/v1/rescues/{id}` (+ `/events`, `/allocations`, `/assignments`, `/exceptions`,
`/command-center`), `POST /api/v1/rescues/{id}/coordinate`, `GET /api/v1/network/recipients` and
`/drivers`, `GET /api/v1/decisions` and `POST /api/v1/decisions/{id}/resolve`,
`GET /api/v1/dashboard`, `GET /api/v1/system/agent-status`, `POST /api/v1/demo/hero`.

## Tests and quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy                      # strict
uv run pytest -m "not integration"
RELAY_TEST_DATABASE_URL=postgresql+asyncpg://relay:relay_local_only@localhost:5432/relay \
  uv run pytest -m integration    # real PostgreSQL: migrations, concurrency, hero workflow
cd frontend && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

105 backend tests cover the domain rules, authorization gates, matching and recovery engines,
transactional outbox, the agents with a deterministic model, and the hero workflow (including
repeated runs on a persistent database). GitHub Actions runs all of it on every push.

## Safety

- Food-safety, policy, and lifecycle decisions are deterministic; the LLM handles bounded
  interpretation only.
- Fail-closed guards reject authoritative safety language from any agent output.
- Donor text is untrusted data; prompts, donor messages, credentials, and reasoning are excluded from
  telemetry and audit records.
- All rescue state changes are versioned, audited, and idempotent.
- The deployed AgentCore runtime has no tools, no state, and a least-privilege execution role.

## Known limitations

- The Relay API's intake endpoint runs the Strands Intake Agent locally; calling the deployed
  AgentCore runtime from the API is an explicit execution-mode seam that is not wired in yet.
- The hero scenario is synthetic and drives its own events; there are no live donor, driver, or
  recipient integrations and no external notifications.
- Routes come from a static demo provider, not a live routing service.
- The AgentCore package intentionally ships no OTLP/ADOT exporter, so application-level X-Ray
  spans are not emitted (runtime logs and Transaction Search are).
- Single-region, single-instance demo deployment; no multi-tenant authentication.

## Documentation

- [Architecture](docs/architecture.md)
- [Autonomy and safety](docs/autonomy-and-safety.md)
- [Relay agents and Strands architecture](docs/agents.md)
- [Matching and recovery](docs/matching-and-recovery.md)
- [Transactional event processing](docs/event-processing.md)
- [AgentCore deployment](docs/agentcore-deployment.md)
- [Devpost submission](docs/devpost-submission.md) · [Demo script](docs/demo-script.md) · [Submission checklist](docs/submission-checklist.md)

## License

Relay is released under the [MIT License](LICENSE).
