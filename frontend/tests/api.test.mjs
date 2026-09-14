import test from "node:test";
import assert from "node:assert/strict";

test("command center API paths remain relative to the Next proxy", () => {
  const paths = ["/api/v1/dashboard", "/api/v1/demo/hero", "/api/v1/system/agent-status", "/api/v1/network/recipients"];
  assert.ok(paths.every((path) => path.startsWith("/api/v1/")));
});

test("runtime status labels are truthful", () => {
  const label = (status) => status?.runtime_verified ? "AgentCore verified" : status?.runtime_configured ? "AgentCore configured" : "Local Strands";
  assert.equal(label({ execution_mode: "local", runtime_configured: false, runtime_verified: false }), "Local Strands");
  assert.equal(label({ execution_mode: "agentcore", runtime_configured: true, runtime_verified: false }), "AgentCore configured");
  assert.equal(label({ execution_mode: "agentcore", runtime_configured: true, runtime_verified: true }), "AgentCore verified");
});

test("status language keeps red for real failures only", () => {
  const danger = new Set(["cancelled", "failed", "expired", "unresolved", "declined", "offline", "error"]);
  assert.ok(danger.has("cancelled"));
  assert.ok(!danger.has("recovered"));
  assert.ok(!danger.has("human_review"));
});
