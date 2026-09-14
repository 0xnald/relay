# Submission checklist

Companion to [devpost-submission.md](devpost-submission.md) and [demo-script.md](demo-script.md).

## Screenshots for Devpost

Capture at 1440×900 from the public command center (https://relay-command-center-three.vercel.app)
unless noted. Use real state only — run the hero scenario first, never edit or mock a screenshot.

| # | File name | What to capture | Where |
| --- | --- | --- | --- |
| 1 | `01-overview.png` | Overview with the metric tiles, one completed rescue in the table ("3 resolved"), and the "Relay control boundary" panel | Overview |
| 2 | `02-rescue-detail.png` | Rescue header (Market Square → verified delivery, Completed, trace ID) with "Food and handling" and "Assignments and recovery" visible | Open the rescue |
| 3 | `03-reassignment.png` | "Assignments and recovery": `36 meals → Harbor · Cancelled`, `36 meals → Riverside · Reserved`, `12 items → Harbor · Reserved`, driver rows with Maya cancelled and the replacement reserved | Rescue detail |
| 4 | `04-decision-card.png` | Decisions view: "Prepared-food preparation time evidence is missing" — status Resolved | Decisions |
| 5 | `05-timeline-human-decision.png` | Timeline segment "Missing Information → Human Decision Received (approve documented exception) → Workflow Resumed" | Rescue detail, timeline |
| 6 | `06-receipt.png` | "Exceptions and recoveries" (three Recovered rows) beside "Delivery receipt — ✓ Delivery verified" | Rescue detail, bottom |
| 7 | `07-architecture.png` | Export of `docs/architecture.svg` | Repo |
| 8 | `08-agentcore-runtime.png` | AWS console: AgentCore runtime `relay_intake`, status READY, Python 3.12, CodeZip (crop out the account ID) | AWS console, us-east-1 |
| 9 | `09-cloudwatch-invocations.png` | CloudWatch log group `/aws/bedrock-agentcore/runtimes/RelayIntake_relay_intake-hT8Z8OBxX6-DEFAULT` with per-session streams; one `Invocation completed successfully` event and the `Invocation failed … AgentInterpretationFailure` event | CloudWatch, us-east-1 |

Optional: `10-demo-control.png` (Demo Control page before clicking) and `11-network.png`
(Network view with the synthetic recipients and drivers).

Do not include screenshots of local `localhost` sessions, IAM pages, Railway/Vercel dashboards,
or anything showing credentials, session tokens, or private URLs.

## Compliance

| Requirement | Status | Evidence |
| --- | --- | --- |
| Public GitHub repository | ✅ | https://github.com/0xnald/relay |
| Source code available | ✅ | Backend, frontend, AgentCore project, scripts, migrations, tests |
| README complete | ✅ | Problem, what it does, hero workflow, autonomy model, safety boundary, Strands, AgentCore, architecture, setup, demo, tests, limitations, license |
| Architecture diagram | ✅ | `docs/architecture.svg`, embedded in README and `docs/architecture.md` |
| License present and visible | ✅ | `LICENSE` (MIT), linked from the README header table and footer |
| Strands Agents usage clearly visible | ✅ | `backend/app/agents/`, `backend/app/tools/strands.py`, README "Strands Agents" section, `docs/agents.md` |
| Amazon Bedrock AgentCore usage | ✅ | Deployed `relay_intake` runtime; `backend/agentcore_runtime.py`; `docs/agentcore-deployment.md` |
| Public frontend URL works | ✅ | https://relay-command-center-three.vercel.app (all views verified, hero scenario run publicly) |
| Public backend URL works | ✅ | https://relay-api-production-721e.up.railway.app/health |
| Demo video plan under 5 minutes | ✅ | `docs/demo-script.md`, target 4:40–4:55 |
| No credentials or secrets committed | ✅ | `.env*` ignored; Railway/Vercel/AWS secrets live only in the hosts; deployed-state and aws-targets carry resource identifiers only |
| No private URLs in submission docs | ✅ | Only the Vercel and Railway public URLs and the GitHub repo |
| AWS Builder ID | ⚠️ manual | Register / sign in with an AWS Builder ID on Devpost before submitting (hackathon requirement); not something the repo can prove |
| Track selected | ⚠️ manual | Select **Good Neighbor Agents** on the Devpost submission form |
| Demo video uploaded | ⚠️ manual | Record per `docs/demo-script.md`, upload, and add the link to the Devpost form and `docs/devpost-submission.md` |

## Pre-submission run-through

1. Open the public demo, run the hero scenario once, confirm the rescue completes with a verified
   receipt.
2. `curl https://relay-api-production-721e.up.railway.app/ready` returns `"status":"ready"`.
3. Confirm the AgentCore runtime status is READY in the console (do not redeploy).
4. Record the video; check the length is under 5:00.
5. Fill the Devpost form from `docs/devpost-submission.md`; attach screenshots 1–9.
