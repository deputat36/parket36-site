export const CALLBACK_PHONE_MIN_DIGITS = 10;
export const CALLBACK_PHONE_MAX_DIGITS = 15;

export function callbackPhoneDigits(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(/\D/g, "");
}

export function contactHasCallbackPhone(value: unknown): boolean {
  const digits = callbackPhoneDigits(value);
  return digits.length >= CALLBACK_PHONE_MIN_DIGITS && digits.length <= CALLBACK_PHONE_MAX_DIGITS;
}
