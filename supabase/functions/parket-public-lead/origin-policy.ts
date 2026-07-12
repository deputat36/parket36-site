export type OriginPolicyDecision = {
  allowed: boolean;
  error: "" | "origin_required" | "origin_not_allowed";
  reason: "allowed_origin" | "healthcheck_token" | "origin_required" | "origin_not_allowed";
};

export function evaluateOriginPolicy(
  origin: string,
  allowedOrigins: readonly string[],
  healthcheckAuthorized: boolean,
): OriginPolicyDecision {
  const normalizedOrigin = origin.trim();

  if (normalizedOrigin) {
    if (allowedOrigins.includes(normalizedOrigin)) {
      return { allowed: true, error: "", reason: "allowed_origin" };
    }
    return { allowed: false, error: "origin_not_allowed", reason: "origin_not_allowed" };
  }

  if (healthcheckAuthorized) {
    return { allowed: true, error: "", reason: "healthcheck_token" };
  }

  return { allowed: false, error: "origin_required", reason: "origin_required" };
}
