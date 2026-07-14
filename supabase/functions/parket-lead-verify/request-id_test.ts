import { validateRequestId } from "./request-id.ts";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

Deno.test("validateRequestId accepts controlled smoke IDs", () => {
  for (const value of [
    "smoke-29349576028-1",
    "parket.controlled:2026_07_14",
    "request-12345678",
  ]) {
    const result = validateRequestId(value);
    assert(result.ok, `valid request_id should be accepted: ${value}`);
  }
});

Deno.test("validateRequestId trims surrounding whitespace", () => {
  const result = validateRequestId("  smoke-12345678  ");
  assert(result.ok, "trimmed request_id should be accepted");
  if (!result.ok) return;
  assert(result.value === "smoke-12345678", "request_id should be normalized");
});

Deno.test("validateRequestId rejects missing and malformed IDs", () => {
  for (const value of [
    "",
    "short",
    "request id with spaces",
    "request/with/slashes",
    12345678,
    null,
  ]) {
    const result = validateRequestId(value);
    assert(!result.ok, `invalid request_id should be rejected: ${String(value)}`);
  }
});

Deno.test("validateRequestId rejects oversized IDs", () => {
  const result = validateRequestId("x".repeat(121));
  assert(!result.ok, "oversized request_id should be rejected");
});
