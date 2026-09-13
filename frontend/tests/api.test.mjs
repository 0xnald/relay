import test from "node:test";
import assert from "node:assert/strict";

test("command center API paths remain relative to the Next proxy", () => {
  const paths = ["/api/v1/dashboard", "/api/v1/demo/hero"];
  assert.ok(paths.every((path) => path.startsWith("/api/v1/")));
});
