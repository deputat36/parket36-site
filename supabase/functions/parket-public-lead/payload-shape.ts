export const LEAD_STRING_FIELDS = Object.freeze([
  "request_id",
  "service",
  "location",
  "area",
  "photos",
  "video",
  "task",
  "callback_time",
  "contact",
  "page",
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "website",
  "company",
] as const);

export type LeadPayload = Record<string, unknown>;

export type PayloadShapeResult =
  | { ok: true; body: LeadPayload }
  | {
      ok: false;
      status: 400 | 422;
      error: "invalid_payload" | "invalid_field_type";
      field: string;
      expected: "object" | "string" | "boolean";
      received: string;
    };

function valueType(value: unknown) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

export function validateLeadPayload(value: unknown): PayloadShapeResult {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return {
      ok: false,
      status: 400,
      error: "invalid_payload",
      field: "payload",
      expected: "object",
      received: valueType(value),
    };
  }

  const body = value as LeadPayload;

  for (const field of LEAD_STRING_FIELDS) {
    if (!(field in body)) continue;
    if (typeof body[field] !== "string") {
      return {
        ok: false,
        status: 422,
        error: "invalid_field_type",
        field,
        expected: "string",
        received: valueType(body[field]),
      };
    }
  }

  if ("test_mode" in body && typeof body.test_mode !== "boolean") {
    return {
      ok: false,
      status: 422,
      error: "invalid_field_type",
      field: "test_mode",
      expected: "boolean",
      received: valueType(body.test_mode),
    };
  }

  return { ok: true, body };
}
