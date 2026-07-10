begin;

create or replace function public.parket_retention_preview(
  p_audit_before timestamptz,
  p_lead_before timestamptz,
  p_lead_statuses text[]
)
returns table (
  audit_rows bigint,
  lead_rows bigint
)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if p_audit_before is null or p_lead_before is null then
    raise exception 'retention cutoffs are required';
  end if;

  if p_audit_before >= now() or p_lead_before >= now() then
    raise exception 'retention cutoffs must be in the past';
  end if;

  if p_lead_statuses is null or cardinality(p_lead_statuses) = 0 then
    raise exception 'at least one completed lead status is required';
  end if;

  if exists (
    select 1
    from unnest(p_lead_statuses) as requested_status
    where requested_status not in ('done', 'spam', 'archived')
  ) then
    raise exception 'only done, spam and archived leads may be removed';
  end if;

  return query
  select
    (
      select count(*)
      from public.parket_public_lead_audit
      where created_at < p_audit_before
    )::bigint,
    (
      select count(*)
      from public.parket_leads
      where created_at < p_lead_before
        and status = any(p_lead_statuses)
    )::bigint;
end;
$$;

create or replace function public.parket_apply_retention(
  p_audit_before timestamptz,
  p_lead_before timestamptz,
  p_lead_statuses text[]
)
returns table (
  deleted_audit bigint,
  deleted_leads bigint
)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  audit_count bigint := 0;
  lead_count bigint := 0;
begin
  if p_audit_before is null or p_lead_before is null then
    raise exception 'retention cutoffs are required';
  end if;

  if p_audit_before >= now() or p_lead_before >= now() then
    raise exception 'retention cutoffs must be in the past';
  end if;

  if p_lead_statuses is null or cardinality(p_lead_statuses) = 0 then
    raise exception 'at least one completed lead status is required';
  end if;

  if exists (
    select 1
    from unnest(p_lead_statuses) as requested_status
    where requested_status not in ('done', 'spam', 'archived')
  ) then
    raise exception 'only done, spam and archived leads may be removed';
  end if;

  delete from public.parket_public_lead_audit
  where created_at < p_audit_before;
  get diagnostics audit_count = row_count;

  delete from public.parket_leads
  where created_at < p_lead_before
    and status = any(p_lead_statuses);
  get diagnostics lead_count = row_count;

  return query select audit_count, lead_count;
end;
$$;

comment on function public.parket_retention_preview(timestamptz, timestamptz, text[])
is 'Паркет36: read-only preview of rows eligible for retention cleanup. Requires explicit past cutoffs and completed lead statuses.';

comment on function public.parket_apply_retention(timestamptz, timestamptz, text[])
is 'Паркет36: explicit retention cleanup. Never removes new or in_progress leads and is not scheduled automatically.';

revoke all on function public.parket_retention_preview(timestamptz, timestamptz, text[]) from public, anon, authenticated;
revoke all on function public.parket_apply_retention(timestamptz, timestamptz, text[]) from public, anon, authenticated;

grant execute on function public.parket_retention_preview(timestamptz, timestamptz, text[]) to service_role;
grant execute on function public.parket_apply_retention(timestamptz, timestamptz, text[]) to service_role;

commit;
