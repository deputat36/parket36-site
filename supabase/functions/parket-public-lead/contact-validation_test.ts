import {
  callbackPhoneDigits,
  contactHasCallbackPhone,
} from "./contact-validation.ts";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

Deno.test("callbackPhoneDigits keeps only phone digits", () => {
  assert(
    callbackPhoneDigits("Алексей, +7 (900) 123-45-67") === "79001234567",
    "formatted Russian phone must be normalized",
  );
});

Deno.test("contactHasCallbackPhone accepts ten to fifteen digits", () => {
  for (const value of [
    "Иван 9001234567",
    "+7 (900) 123-45-67",
    "+420 777 123 456",
    "+1 202 555 0123",
  ]) {
    assert(contactHasCallbackPhone(value), `valid callback phone rejected: ${value}`);
  }
});

Deno.test("contactHasCallbackPhone rejects unusable contact text", () => {
  for (const value of [
    "Иван",
    "пишите в мессенджер",
    "12345",
    "+7 900 12",
    "+1234567890123456",
    null,
  ]) {
    assert(!contactHasCallbackPhone(value), `invalid callback contact accepted: ${String(value)}`);
  }
});
