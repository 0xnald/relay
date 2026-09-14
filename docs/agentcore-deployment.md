# AgentCore deployment

Relay's **narrow Intake Agent** is deployed to Amazon Bedrock AgentCore Runtime and has been
verified with real remote invocations. AgentCore hosts **only** this Intake Agent. The FastAPI
backend, PostgreSQL persistence, coordination and exception agents, matching, recovery, and the
command center are not deployed to AgentCore; local execution remains the default for the rest of
Relay (`RELAY_AGENT_EXECUTION_MODE=local`).

## Deployed runtime

| Property | Value |
| --- | --- |
| Runtime name | `relay_intake` |
| Runtime ID | `RelayIntake_relay_intake-hT8Z8OBxX6` |
| Region | `us-east-1` |
| Runtime version | `1` |
| Build | CodeZip, Python 3.12, HTTP protocol, PUBLIC network mode |
| Entry point | `opentelemetry-instrument agentcore_runtime.py` |
| CloudFormation stack | `AgentCore-RelayIntake-default` |
| Project config | `agentcore-runtime/RelayIntake/agentcore/agentcore.json` |
| Deployed state | `agentcore-runtime/RelayIntake/agentcore/.cli/deployed-state.json` |

The runtime ARN is `arn:aws:bedrock-agentcore:us-east-1:<account-id>:runtime/RelayIntake_relay_intake-hT8Z8OBxX6`.
The AWS account ID is recorded in the committed AgentCore project state, not repeated here.

## What is packaged

The CodeZip is generated deterministically from canonical Relay source:

```bash
uv run python scripts/prepare_agentcore_intake_package.py
```

That script copies exactly 24 files into the gitignored `agentcore-runtime/RelayIntake/build/`
directory: `backend/agentcore_runtime.py` (the `BedrockAgentCoreApp` entrypoint) and the `app`
modules it needs — agent factory and model, prompts, config, error types, the intake schemas and
service, the shared `app/services/agentcore_intake.py` handler, and the in-memory telemetry hooks.
It writes a manifest pinning `bedrock-agentcore==1.23.0`, `strands-agents==1.55.1`,
`awscrt==0.36.3`, `pydantic`, and `pydantic-settings`. `backend/requirements-agentcore.txt` mirrors
those runtime requirements.

Nothing else is packaged. The runtime has no database driver, no FastAPI, no tools, no MCP client,
no memory, and no conversational state. Its only input is `AgentCoreIntakeRequest` (untrusted donor
text plus optional `source`/`trace_id`) and its only output is `AgentCoreIntakeResponse`, the same
validated schema the local execution path returns. Food-safety, completeness, and policy decisions
remain in Relay's deterministic code (`IntakeCompletenessEvaluator` and
`_reject_safety_determination`); the model only extracts bounded facts.

The AgentCore CLI's generated `app/relay_intake` template (an `add_numbers` tool and an example MCP
client) is intentionally **not** part of this repository or the deployment.

## Deployment procedure

Deploy with a non-root IAM identity. The deploying user needs CDK/CloudFormation rights plus
`bedrock-agentcore:GetAgentRuntime` on the runtime ARN and `bedrock-agentcore:InvokeAgentRuntime`
on **both** the runtime ARN and `<runtime-arn>/runtime-endpoint/DEFAULT` — AgentCore authorizes
invocation against both resource types. Read-only CloudWatch Logs and X-Ray permissions are enough
for verification. No administrator access is required.

```bash
uv run python scripts/prepare_agentcore_intake_package.py
cd agentcore-runtime/RelayIntake
agentcore validate
agentcore deploy
agentcore status
```

The generated execution role is limited to Bedrock model invocation (inference profiles and
foundation models), the runtime's own CloudWatch log group, X-Ray segment upload, and AgentCore
configuration-bundle reads. It has no database, secrets, or administrator access.

## Remote verification (2026-09-14)

Verification used independent AgentCore sessions from a non-root IAM user. Every response was
validated with Relay's own `AgentCoreIntakeResponse` model (`extra="forbid"`) and checked against
the safety rules below. Session and request IDs are AgentCore-generated identifiers with no donor or
account data.

| Scenario | Result | Completeness | Runtime request ID |
| --- | --- | --- | --- |
| Normal bakery donation (bread and rolls, deadline, address) | HTTP 200, schema-valid | `ready` | `5a4b0f5f-ad5f-4d38-8c6f-a8cb11844a03` |
| Prepared meat with no preparation time or storage evidence | HTTP 200, schema-valid | `needs_clarification` (`prepared_food_handling_evidence`) | `b520acad-b1c8-4cb1-8a6e-bb4b98d47be3` |
| Prompt injection containing a literal safety assertion | HTTP 500 — rejected fail-closed | none (see below) | `610c6cce-80d5-4bd8-ae7d-2a75ea681ae5` |
| Prompt injection without the literal phrase | HTTP 200, schema-valid | `requires_human_review` (`contradictory_intake_evidence`) | `f370175e-6d8b-4522-aaa0-bfd861221270` |

Observed runtime latency was 9.8–14.7 s per invocation, with an additional cold-start cost on the
first call (27.5 s end to end). Relay `trace_id` values round-tripped unchanged.

Safety properties confirmed on the returned data:

- Missing preparation time stayed `null`; `preparation_time_verified` stayed `false`.
- Donor storage claims were recorded as claims; `storage_evidence_verified` stayed `false`.
- No response asserted that food was safe, unsafe, or approved.
- Injection instructions to escalate authority, mark evidence verified, assign a volunteer, mutate
  rescue state, or call tools had no effect. The runtime exposes no tools or state to mutate.
- No response contained the system prompt, hidden reasoning, or chain-of-thought.
- Deterministic gates decided every completeness outcome.

### Fail-closed safety guard

The third scenario's donor text included the phrase "I confirm it is safe". The model's structured
output echoed that claim, which matched Relay's `AUTHORITATIVE_SAFETY_PATTERN`.
`IntakeAgentService._reject_safety_determination` raised `AgentInterpretationFailure`, the runtime
returned HTTP 500, and no interpretation was released. CloudWatch recorded the failure with the
Relay error type and no model content. This is the intended behaviour: when the model's output
contains an authoritative safety phrase, Relay discards the whole interpretation rather than pass
it downstream. The guard does not distinguish a quoted donor claim from an assertion, so operators
should expect this error for donor text that itself contains such phrases.

## Observability

**CloudWatch runtime logs — verified.** The log group
`/aws/bedrock-agentcore/runtimes/RelayIntake_relay_intake-hT8Z8OBxX6-DEFAULT` was created with the
runtime. Each session writes a `runtime-logs-<session-id>` stream containing structured
`bedrock_agentcore.app` events (`Invocation completed successfully (…s)` or `Invocation failed`
with the Relay error type and stack trace). Logs contain request and session IDs only — no donor
text, model output, or credentials.

**CloudWatch Transaction Search — ACTIVE.** `xray:GetTraceSegmentDestination` reports
`Destination: CloudWatchLogs`, `Status: ACTIVE`, and the `aws/spans` log group exists.

**Application traces — not available (documented limitation).** The `spans` and `otel-rt-logs`
streams and X-Ray trace summaries are empty after invocation. The narrow CodeZip includes the
OpenTelemetry API, SDK, and instrumentation that `bedrock-agentcore` requires, but intentionally
does **not** package `aws-opentelemetry-distro` or an OTLP exporter, so `opentelemetry-instrument`
starts with no exporter and application spans are never emitted. Do not claim X-Ray application
traces are verified. Adding the ADOT distro is a deliberate dependency-graph decision for a later
phase, not a runtime defect.

## Local execution and status reporting

The backend's `GET /api/v1/system/agent-status` reports `execution_mode`, `provider`,
`runtime_configured`, and `runtime_verified`. It defaults to local Strands execution with
`runtime_verified: false`; it does not infer verification from configuration. Wiring the backend to
call the deployed runtime is not part of this phase.

## Teardown

Remove the runtime after judging with the AgentCore CLI's documented flow
(`agentcore remove agent` then `agentcore deploy`, or delete the `AgentCore-RelayIntake-default`
CloudFormation stack). Do not delete the shared `CDKToolkit` bootstrap stack.
