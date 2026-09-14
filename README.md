# Relay

**Autonomous food-rescue coordination from intake through verified delivery.**

Relay helps donors, recipient organizations, drivers, and coordinators complete food rescues with
less manual follow-up. It observes operational events, reasons about routine exceptions, acts within
explicit authority, verifies outcomes, attempts safe recovery, and asks a person only when judgment
is required.

> Food rescue does not only have a matching problem. It has a coordination problem.

## The problem

A match between surplus food and a recipient is only the start. Someone still has to confirm
capacity, assign transport, track time windows, collect pickup and delivery evidence, replace a
cancelled driver, respond to partial acceptance, and establish what actually arrived. These small
coordination tasks accumulate quickly and often fall to already stretched people.

Relay is a coordination layer rather than another donation marketplace. It is designed to carry a
rescue through the operational work after intake and matching, while keeping policy, safety, and
consequential decisions under deterministic or human control.

## Operating loop

```text
OBSERVE -> REASON -> ACT -> VERIFY -> RECOVER -> ESCALATE ONLY WHEN NECESSARY
```

- **Observe:** receive typed, idempotent events from donors, recipients, drivers, and systems.
- **Reason:** interpret the situation and plan coordination within known constraints.
- **Act:** use audited tools only after deterministic authorization.
- **Verify:** require evidence for pickup, delivery, and configured handling rules.
- **Recover:** handle routine failures such as declines, cancellations, and timeouts.
- **Escalate:** request human judgment for ambiguity, conflicts, missing critical evidence, and
  potentially unsafe conditions.

## Who Relay serves

- Food donors coordinating recurring or time-sensitive surplus
- Food banks, pantries, shelters, and other recipient organizations
- Volunteer or professional drivers
- Community coordinators overseeing many simultaneous rescues

## Autonomy and food safety

Relay classifies proposed actions into three authority levels:

| Level | Relay behavior | Examples |
| --- | --- | --- |
| Green | Execute autonomously | Search for an alternate recipient, replace a cancelled driver, send status updates |
| Amber | Execute only when an active policy explicitly allows it | Split a rescue, substitute a recipient, extend a pickup window |
| Red | Require a human decision | Override handling requirements, continue with missing evidence, resolve conflicting policies |

An LLM must never decide that food is safe to eat. Future agents may extract facts, identify missing
information, reason about operational exceptions, and compose communications. Deterministic code
validates evidence, time windows, storage constraints, authorization, and lifecycle transitions.
Ambiguous or conflicting safety information fails closed and goes to a human.

See [Autonomy and safety](docs/autonomy-and-safety.md) for the enforceable boundary.

## Architecture

The backend uses Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2, Alembic, and PostgreSQL.
Domain models do not depend on FastAPI, database sessions, or agent frameworks. This separation
keeps lifecycle state, authorization, safety constraints, and business rules outside future model
reasoning.

```mermaid
flowchart LR
    API[API / event intake] --> WF[Workflow application layer]
    WF --> AG[Strands intake and coordination agents]
    AG --> PE[Deterministic policy and safety gates]
    PE --> TL[Audited tools]
    TL --> RP[Repositories and integrations]
    RP --> DB[(PostgreSQL)]
    WF --> SM[Rescue state machine]
    SM --> DB
    PE --> HR[Human decision request]
```

See [Architecture](docs/architecture.md) for component responsibilities and decisions.

## Repository structure

```text
backend/
  app/
    api/              HTTP routes and transport concerns
    core/             settings, errors, logging, request tracing
    domain/           framework-independent entities, events, and policies
    services/         deterministic state and safety services
    repositories/     persistence boundaries and database lifecycle
    models/           SQLAlchemy persistence models
    schemas/          validated transport and structured-output schemas
    agents/           Strands agent factory, model configuration, and prompts
    tools/            bounded Strands and audited application tools
    workflows/        reserved for application orchestration
    observability/    observability adapters
    integrations/     external system adapters
  migrations/         Alembic migration environment and revisions
  tests/              deterministic unit and API tests
docs/                 architecture and safety decisions
```

## Local development

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), and PostgreSQL for development or
production persistence. SQLite is used only for fast isolated tests. The included Compose file pins
the same PostgreSQL release used in CI.

```bash
git clone https://github.com/0xnald/relay.git
cd relay
cp .env.example .env
uv sync --dev
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload
```

Set `RELAY_DATABASE_URL` in `.env` to a reachable PostgreSQL database before running migrations.
The local values in `.env.example` match the Compose service and are development credentials only.

The API exposes:

- `GET /health` for process liveness
- `GET /ready` for database-backed readiness
- `POST /api/v1/events` for typed, idempotent event ingestion
- `POST /api/v1/agent/intake` for validated natural-language donation intake
- `GET /api/v1/rescues/{rescue_id}` for rescue state
- `GET /api/v1/rescues/{rescue_id}/events` for ordered event history
- `POST /api/v1/rescues/{rescue_id}/coordinate` for a bounded coordination proposal
- `GET /api/v1/network/recipients` and `/drivers` for operational network views
- `GET /api/v1/rescues/{rescue_id}/allocations`, `/assignments`, and `/exceptions`
- `GET /api/v1/decisions` and `GET/POST /api/v1/decisions/{decision_id}` for human review
- `GET /api/v1/dashboard`, rescue command-center detail, and `POST /api/v1/demo/hero` for the
  synthetic operator demo (disabled when `RELAY_ENVIRONMENT=production`)

Event requests require an `Idempotency-Key` header. A valid `X-Request-ID` is propagated when
provided; otherwise Relay generates one.

## Command center demo

Phase 5 adds a local Next.js command center that talks to the FastAPI service through a development
proxy. Start PostgreSQL and the backend as above, then run the frontend in another terminal:

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Open `http://localhost:3000` and choose **Run synthetic hero demo**. That control calls the real
backend hero workflow, then displays the persisted rescue, food allocations, driver cancellation and
recovery, evidence decision, and verified-delivery receipt. Organizations, metrics, and route labels
in this view are synthetic demo data. The UI does not imply live dispatch, external messages, or an
Amazon Bedrock AgentCore deployment.

For a recording-oriented control page, open `http://localhost:3000/demo`. The command center polls
the backend every three seconds so other views refresh from persisted state without browser reloads.

## Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m "not integration"
RELAY_TEST_DATABASE_URL=postgresql+asyncpg://relay:relay_local_only@localhost:5432/relay \
  uv run pytest -m integration
```

Run all four with `make check` on systems with Make. GitHub Actions runs the same checks on every
push and pull request.

## Phase status and roadmap

Phase 1 established typed domain primitives, lifecycle and authority rules, food-safety boundaries,
and the initial API and database foundation.

Phase 2 adds repository and unit-of-work boundaries, persistent versioned rescue transitions,
idempotent event processing, action and tool authorization, database readiness, minimal event/rescue
APIs, and real PostgreSQL integration coverage. See
[Transactional event processing](docs/event-processing.md).

Phase 3 adds real Strands Agents SDK orchestration for structured donation intake and bounded rescue
coordination. It includes Bedrock model configuration, six application-backed tools, deterministic
authority and completeness checks, safe lifecycle hooks, queued clarifications, invocation audit
records, and offline deterministic tests. See [Relay agents and Strands architecture](docs/agents.md).

Phase 4 adds the persisted synthetic rescue network, deterministic route/eligibility/feasibility and
scoring engines, atomic capacity and driver assignment, operational exception recovery, the bounded
Strands Exception Agent, human pause/resume, and the transactional outbox. The executable backend
hero scenario reaches verified delivery through real services without AWS access:

```bash
uv run python scripts/run_hero_scenario.py
```

See [Matching and recovery](docs/matching-and-recovery.md) for the scoring formula, locking model,
recovery flow, and demo constraints. Later phases will add external notification providers, a user
interface, and Amazon Bedrock AgentCore deployment. Relay does not claim live routing or external
message delivery in Phase 4.

Phase 5 adds the judge-facing local operations command center and backend dashboard endpoints. Its
single demo control runs the existing executable hero scenario through real repositories, workflow
services, state transitions, exception recovery, and receipt verification. It does not add AgentCore
or external operational integrations.

Phase 6 deploys Relay's narrow Intake Agent to Amazon Bedrock AgentCore Runtime (`relay_intake`,
Python 3.12 CodeZip, `us-east-1`) and verifies it with real remote invocations: a normal donation
returns `ready`, missing handling evidence returns `needs_clarification`, a hostile prompt returns
`requires_human_review`, and output containing an authoritative safety phrase is rejected
fail-closed by Relay's deterministic guard. CloudWatch runtime logs and Transaction Search are
verified; application X-Ray spans are not, because the narrow package intentionally ships no OTLP
exporter. AgentCore hosts only the Intake Agent, not the backend. See
[AgentCore deployment](docs/agentcore-deployment.md).

## License

[MIT](LICENSE)
