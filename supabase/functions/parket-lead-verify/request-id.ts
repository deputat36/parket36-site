export const REQUEST_ID_MIN_LENGTH = 8;
export const REQUEST_ID_MAX_LENGTH = 120;
export const REQUEST_ID_PATTERN = /^[a-zA-Z0-9._:-]+$/;

export type RequestIdValidation =
  | { ok: true; value: string }
  | { ok: false; error: "request_id_required" | "request_id_invalid" };

export function validateRequestId(value: unknown): RequestIdValidation {
  if (typeof value !== "string" || !value.trim()) {
    return { ok: false, error: "request_id_required" };
  }

  const normalized = value.trim();
  if (
    normalized.length < REQUEST_ID_MIN_LENGTH ||
    normalized.length > REQUEST_ID_MAX_LENGTH ||
    !REQUEST_ID_PATTERN.test(normalized)
  ) {
    return { ok: false, error: "request_id_invalid" };
  }

  return { ok: true, value: normalized };
}
