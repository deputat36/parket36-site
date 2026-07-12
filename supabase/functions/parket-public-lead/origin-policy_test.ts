import { evaluateOriginPolicy } from "./origin-policy.ts";

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const allowedOrigins = ["https://parket36.ru", "https://www.parket36.ru"];

Deno.test("origin policy accepts configured browser origin", () => {
  const decision = evaluateOriginPolicy("https://parket36.ru", allowedOrigins, false);
  assert(decision.allowed, "configured origin should be allowed");
  assert(decision.reason === "allowed_origin", "configured origin reason should be allowed_origin");
});

Deno.test("origin policy rejects unknown browser origin", () => {
  const decision = evaluateOriginPolicy("https://example.org", allowedOrigins, false);
  assert(!decision.allowed, "unknown origin should be rejected");
  assert(decision.error === "origin_not_allowed", "unknown origin should return origin_not_allowed");
});

Deno.test("origin policy rejects missing origin for normal requests", () => {
  const decision = evaluateOriginPolicy("", allowedOrigins, false);
  assert(!decision.allowed, "missing origin should be rejected");
  assert(decision.error === "origin_required", "missing origin should return origin_required");
});

Deno.test("origin policy permits token-authorized healthcheck without origin", () => {
  const decision = evaluateOriginPolicy("", allowedOrigins, true);
  assert(decision.allowed, "authorized healthcheck should be allowed without origin");
  assert(decision.reason === "healthcheck_token", "healthcheck reason should be healthcheck_token");
});
