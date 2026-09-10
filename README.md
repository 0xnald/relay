# Relay

Autonomous food-rescue coordination from intake through verified delivery.

Relay is in Phase 1: backend foundations, deterministic domain rules, auditability, and safety
boundaries. Strands Agents integration, AgentCore deployment, and the user interface are planned
for later phases.

## Development

Install dependencies with `uv sync --dev`, then run the API with
`uv run uvicorn app.main:app --app-dir backend --reload`.

Run all quality gates with `make check`, or run `make lint`, `make format-check`,
`make typecheck`, and `make test` separately.
