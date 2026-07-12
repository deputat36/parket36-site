export const LEAD_FIELD_LIMITS = Object.freeze({
  service: 160,
  location: 160,
  area: 80,
  photos: 500,
  video: 500,
  task: 3000,
  callback_time: 160,
  contact: 240,
  page: 500,
  utm_source: 160,
  utm_medium: 160,
  utm_campaign: 220,
  utm_content: 220,
  utm_term: 220,
} as const);

export type LeadFieldName = keyof typeof LEAD_FIELD_LIMITS;

export type OversizedLeadField = {
  field: LeadFieldName;
  limit: number;
  received: number;
};

export function firstOversizedLeadField(body: Record<string, unknown>): OversizedLeadField | null {
  for (const [field, limit] of Object.entries(LEAD_FIELD_LIMITS) as [LeadFieldName, number][]) {
    const value = body[field];
    if (value === null || value === undefined) continue;
    const received = String(value).length;
    if (received > limit) return { field, limit, received };
  }
  return null;
}
