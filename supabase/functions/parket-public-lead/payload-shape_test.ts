import { validateLeadPayload } from "./payload-shape.ts";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

Deno.test("validateLeadPayload accepts the public form contract", () => {
  const result = validateLeadPayload({
    request_id: "request-12345678",
    service: "Циклёвка паркета",
    task: "Нужно оценить старый паркет",
    contact: "Алексей, +7 900 000-00-00",
    website: "",
    company: "",
  });

  assert(result.ok, "string-based public form payload should be accepted");
});

Deno.test("validateLeadPayload accepts protected test mode", () => {
  const result = validateLeadPayload({ test_mode: true });
  assert(result.ok, "boolean test_mode should be accepted");
});

Deno.test("validateLeadPayload rejects null, arrays and scalar JSON", () => {
  for (const value of [null, [], "lead", 42, true]) {
    const result = validateLeadPayload(value);
    assert(!result.ok, `invalid top-level payload should be rejected: ${String(value)}`);
    if (result.ok) continue;
    assert(result.status === 400, "invalid top-level payload should return 400");
    assert(result.error === "invalid_payload", "invalid top-level payload should use invalid_payload");
    assert(result.field === "payload", "invalid top-level payload should identify payload");
  }
});

Deno.test("validateLeadPayload rejects non-string lead fields", () => {
  const result = validateLeadPayload({
    task: { text: "Нужно оценить паркет" },
    contact: "Алексей, +7 900 000-00-00",
  });

  assert(!result.ok, "object task should be rejected");
  if (result.ok) return;
  assert(result.status === 422, "invalid field type should return 422");
  assert(result.error === "invalid_field_type", "invalid field type should use invalid_field_type");
  assert(result.field === "task", "invalid field type should identify task");
  assert(result.expected === "string", "task should require a string");
  assert(result.received === "object", "received type should be reported");
});

Deno.test("validateLeadPayload rejects contact without a usable phone", () => {
  for (const contact of ["Позвоните мне", "Иван, 12345", "1234567890123456"]) {
    const result = validateLeadPayload({
      task: "Нужно оценить состояние пола",
      contact,
    });

    assert(!result.ok, `invalid contact should be rejected: ${contact}`);
    if (result.ok) continue;
    assert(result.status === 422, "invalid phone should return 422");
    assert(result.error === "contact_phone_invalid", "invalid phone should use contact_phone_invalid");
    assert(result.field === "contact", "invalid phone should identify contact");
    assert(result.expected === "10-15 digits", "phone contract should be reported");
    assert(typeof result.received === "number", "received digit count should be numeric");
  }
});

Deno.test("validateLeadPayload leaves empty contact to required-field validation", () => {
  const result = validateLeadPayload({
    task: "Нужно оценить состояние пола",
    contact: "",
  });
  assert(result.ok, "empty string has a valid shape and is rejected later as a required field");
});

Deno.test("validateLeadPayload rejects non-boolean test mode", () => {
  const result = validateLeadPayload({ test_mode: "true" });

  assert(!result.ok, "string test_mode should be rejected");
  if (result.ok) return;
  assert(result.status === 422, "invalid test_mode type should return 422");
  assert(result.field === "test_mode", "invalid test_mode should identify the field");
  assert(result.expected === "boolean", "test_mode should require a boolean");
});
