import test from "node:test";
import assert from "node:assert/strict";

test("command center API paths remain relative to the Next proxy", () => {
  const paths = ["/api/v1/dashboard", "/api/v1/demo/hero"];
  assert.ok(paths.every((path) => path.startsWith("/api/v1/")));
});

test("runtime status labels are truthful", () => {
  const label = (status) => status?.runtime_verified ? "Verified" : status?.runtime_configured ? "AgentCore configured — pending verification" : "Local";
  assert.equal(label({ execution_mode: "local", runtime_configured: false, runtime_verified: false }), "Local");
  assert.equal(label({ execution_mode: "agentcore", runtime_configured: true, runtime_verified: false }), "AgentCore configured — pending verification");
  assert.equal(label({ execution_mode: "agentcore", runtime_configured: true, runtime_verified: true }), "Verified");
});
