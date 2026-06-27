begin;

create table if not exists public.parket_leads (
  id uuid primary key default gen_random_uuid(),
  request_id text not null unique,
  created_at timestamptz not null default now(),
  status text not null default 'new' check (status in ('new', 'in_progress', 'done', 'spam', 'archived')),
  service text,
  location text,
  area text,
  photos text,
  video text,
  task text not null,
  callback_time text,
  contact text not null,
  page text,
  attribution jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  user_agent text
);

comment on table public.parket_leads is 'Паркет36: заявки с публичной формы оценки пола. Доступ только через Edge Function/service role; публичные роли не имеют прямого доступа.';
comment on column public.parket_leads.request_id is 'Client-generated idempotency key for duplicate protection.';
comment on column public.parket_leads.contact is 'Client contact text from the public form; contains personal data.';

create index if not exists parket_leads_created_at_idx on public.parket_leads (created_at desc);
create index if not exists parket_leads_status_created_at_idx on public.parket_leads (status, created_at desc);
create index if not exists parket_leads_attribution_gin_idx on public.parket_leads using gin (attribution);

alter table public.parket_leads enable row level security;

revoke all on table public.parket_leads from anon;
revoke all on table public.parket_leads from authenticated;
grant select, insert, update, delete on table public.parket_leads to service_role;

create table if not exists public.parket_public_lead_audit (
  id uuid primary key default gen_random_uuid(),
  request_id text,
  created_at timestamptz not null default now(),
  origin text,
  ip_hash text,
  user_agent text,
  accepted boolean not null default false,
  reason text,
  payload_summary jsonb not null default '{}'::jsonb
);

comment on table public.parket_public_lead_audit is 'Паркет36: аудит публичных отправок формы и мягкий антиспам. IP хранится только в виде SHA-256 hash.';

create index if not exists parket_public_lead_audit_created_at_idx on public.parket_public_lead_audit (created_at desc);
create index if not exists parket_public_lead_audit_ip_hash_created_at_idx on public.parket_public_lead_audit (ip_hash, created_at desc);
create index if not exists parket_public_lead_audit_request_id_idx on public.parket_public_lead_audit (request_id);

alter table public.parket_public_lead_audit enable row level security;

revoke all on table public.parket_public_lead_audit from anon;
revoke all on table public.parket_public_lead_audit from authenticated;
grant select, insert, update, delete on table public.parket_public_lead_audit to service_role;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'parket_leads'
      and policyname = 'parket_leads_no_public_direct_access'
  ) then
    create policy parket_leads_no_public_direct_access
    on public.parket_leads
    as restrictive
    for all
    to anon, authenticated
    using (false)
    with check (false);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'parket_public_lead_audit'
      and policyname = 'parket_public_lead_audit_no_public_direct_access'
  ) then
    create policy parket_public_lead_audit_no_public_direct_access
    on public.parket_public_lead_audit
    as restrictive
    for all
    to anon, authenticated
    using (false)
    with check (false);
  end if;
end $$;

commit;
