# AgentCore deployment

## VERIFIED LOCALLY

Relay uses Python 3.12, Strands 1.55.1, and `awscrt` so the SDK can use AWS CLI login credentials. The narrow `backend/agentcore/intake.py` entrypoint accepts only validated intake text and returns Relay's validated schema; it has no database mutation or arbitrary tools. Local execution remains the default.

## BLOCKED BY AWS VERIFICATION

AWS identity and the `us-east-1` inference profile `global.anthropic.claude-sonnet-4-6` were verified. Relay's real Bedrock smoke request reached `ConverseStream`, which AWS denied while the account is under verification. This is not treated as a model, safety, or IAM workaround.

## NOT YET ATTEMPTED

After verification clears, use the local AWS CLI at `C:\Users\REGGIEHUBS\AppData\Local\Programs\Amazon\AWSCLIV2\aws.exe`, run `aws sts get-caller-identity`, then `RELAY_RUN_LIVE_BEDROCK=1 uv run python scripts/smoke_intake_agent.py`. Follow the current AWS AgentCore CLI direct-code deployment procedure (`agentcore create`, `agentcore deploy`, `agentcore invoke`) for the Intake entrypoint only. Enable CloudWatch Transaction Search before deployment, then record the runtime ARN, session/invocation IDs, Relay trace ID, and CloudWatch trace/log group. Do not mark a runtime verified until a remote validated response and trace are visible.

Use a least-privilege execution role limited to Bedrock invocation and AgentCore/CloudWatch runtime telemetry. Do not grant database, secrets, or administrator access. Teardown follows the generated AgentCore project's documented delete flow after judging.
