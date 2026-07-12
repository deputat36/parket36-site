import { assertEquals } from "jsr:@std/assert@1";
import { firstOversizedLeadField, LEAD_FIELD_LIMITS } from "./field-limits.ts";

Deno.test("lead field limits match public form contract", () => {
  assertEquals(LEAD_FIELD_LIMITS.location, 160);
  assertEquals(LEAD_FIELD_LIMITS.area, 80);
  assertEquals(LEAD_FIELD_LIMITS.task, 3000);
  assertEquals(LEAD_FIELD_LIMITS.callback_time, 160);
  assertEquals(LEAD_FIELD_LIMITS.contact, 240);
});

Deno.test("firstOversizedLeadField accepts exact limits", () => {
  assertEquals(firstOversizedLeadField({
    location: "л".repeat(160),
    area: "м".repeat(80),
    task: "т".repeat(3000),
    callback_time: "в".repeat(160),
    contact: "к".repeat(240),
  }), null);
});

Deno.test("firstOversizedLeadField reports field, limit and received length", () => {
  assertEquals(firstOversizedLeadField({
    location: "Воронеж",
    task: "т".repeat(3001),
    contact: "Иван, +7 900 000-00-00",
  }), {
    field: "task",
    limit: 3000,
    received: 3001,
  });
});
