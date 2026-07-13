import { assertEquals } from "jsr:@std/assert@1";
import {
  CONTACT_PHONE_MAX_DIGITS,
  CONTACT_PHONE_MIN_DIGITS,
  contactPhoneDigitCount,
  validateContactPhone,
} from "./contact-validation.ts";

Deno.test("contact phone contract matches the public form", () => {
  assertEquals(CONTACT_PHONE_MIN_DIGITS, 10);
  assertEquals(CONTACT_PHONE_MAX_DIGITS, 15);
});

Deno.test("contactPhoneDigitCount ignores names and punctuation", () => {
  assertEquals(contactPhoneDigitCount("Иван, +7 (900) 123-45-67"), 11);
  assertEquals(contactPhoneDigitCount("Call me: +31 6 1234 5678"), 11);
});

Deno.test("validateContactPhone accepts 10 to 15 digits", () => {
  assertEquals(validateContactPhone("8 900 123-45-67"), { ok: true, digits: 11 });
  assertEquals(validateContactPhone("+44 20 7946 0958"), { ok: true, digits: 12 });
  assertEquals(validateContactPhone("1234567890"), { ok: true, digits: 10 });
  assertEquals(validateContactPhone("123456789012345"), { ok: true, digits: 15 });
});

Deno.test("validateContactPhone rejects text, short and oversized numbers", () => {
  assertEquals(validateContactPhone("Позвоните мне"), {
    ok: false,
    digits: 0,
    minDigits: 10,
    maxDigits: 15,
  });
  assertEquals(validateContactPhone("Иван, 12345"), {
    ok: false,
    digits: 5,
    minDigits: 10,
    maxDigits: 15,
  });
  assertEquals(validateContactPhone("1234567890123456"), {
    ok: false,
    digits: 16,
    minDigits: 10,
    maxDigits: 15,
  });
});
