export const CONTACT_PHONE_MIN_DIGITS = 10;
export const CONTACT_PHONE_MAX_DIGITS = 15;

export type ContactPhoneValidation =
  | { ok: true; digits: number }
  | {
      ok: false;
      digits: number;
      minDigits: number;
      maxDigits: number;
    };

export function contactPhoneDigitCount(value: string) {
  return (value.match(/[0-9]/g) || []).length;
}

export function validateContactPhone(value: string): ContactPhoneValidation {
  const digits = contactPhoneDigitCount(value);
  if (digits >= CONTACT_PHONE_MIN_DIGITS && digits <= CONTACT_PHONE_MAX_DIGITS) {
    return { ok: true, digits };
  }

  return {
    ok: false,
    digits,
    minDigits: CONTACT_PHONE_MIN_DIGITS,
    maxDigits: CONTACT_PHONE_MAX_DIGITS,
  };
}
