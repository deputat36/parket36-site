-- Паркет36: воспроизводимая read-only проверка production-объектов.
--
-- Скрипт ничего не создаёт, не изменяет и не удаляет. Он проверяет только:
--   * существование и RLS двух таблиц заявок;
--   * политики и прямые табличные права;
--   * SECURITY DEFINER и ACL служебных retention-функций;
--   * число строк и использование индексов.
--
-- Ожидаемый безопасный контракт:
--   * RLS включён на parket_leads и parket_public_lead_audit;
--   * anon/authenticated имеют явную deny-all policy и не имеют табличных GRANT;
--   * parket_* retention-функции исполняются только postgres/service_role;
--   * проверка не вызывает Edge Function и не создаёт тестовую заявку.

with parket_tables as (
  select
    c.oid,
    n.nspname as schema_name,
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced,
    coalesce(s.n_live_tup, 0) as estimated_rows
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  left join pg_stat_user_tables s
    on s.relid = c.oid
  where n.nspname = 'public'
    and c.relkind = 'r'
    and c.relname in ('parket_leads', 'parket_public_lead_audit')
),
policy_snapshot as (
  select
    schemaname as schema_name,
    tablename as table_name,
    count(*) as policy_count,
    jsonb_agg(
      jsonb_build_object(
        'name', policyname,
        'roles', roles,
        'command', cmd,
        'using', qual,
        'with_check', with_check
      )
      order by policyname
    ) as policies
  from pg_policies
  where schemaname = 'public'
    and tablename in ('parket_leads', 'parket_public_lead_audit')
  group by schemaname, tablename
),
grant_snapshot as (
  select
    table_schema as schema_name,
    table_name,
    jsonb_agg(
      jsonb_build_object(
        'grantee', grantee,
        'privilege', privilege_type
      )
      order by grantee, privilege_type
    ) as grants
  from information_schema.role_table_grants
  where table_schema = 'public'
    and table_name in ('parket_leads', 'parket_public_lead_audit')
    and grantee in ('PUBLIC', 'anon', 'authenticated', 'service_role', 'postgres')
  group by table_schema, table_name
),
index_snapshot as (
  select
    schemaname as schema_name,
    relname as table_name,
    jsonb_agg(
      jsonb_build_object(
        'index', indexrelname,
        'scans', idx_scan,
        'tuples_read', idx_tup_read,
        'tuples_fetched', idx_tup_fetch
      )
      order by indexrelname
    ) as indexes
  from pg_stat_user_indexes
  where schemaname = 'public'
    and relname in ('parket_leads', 'parket_public_lead_audit')
  group by schemaname, relname
),
function_snapshot as (
  select
    n.nspname as schema_name,
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as arguments,
    p.prosecdef as security_definer,
    coalesce(array_to_json(p.proacl), '[]'::json) as acl
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public'
    and p.proname in ('parket_retention_preview', 'parket_apply_retention')
)
select jsonb_build_object(
  'generated_at', now(),
  'tables', coalesce(
    jsonb_agg(
      jsonb_build_object(
        'table', t.table_name,
        'estimated_rows', t.estimated_rows,
        'rls_enabled', t.rls_enabled,
        'rls_forced', t.rls_forced,
        'policy_count', coalesce(p.policy_count, 0),
        'policies', coalesce(p.policies, '[]'::jsonb),
        'grants', coalesce(g.grants, '[]'::jsonb),
        'indexes', coalesce(i.indexes, '[]'::jsonb)
      )
      order by t.table_name
    ),
    '[]'::jsonb
  ),
  'functions', (
    select coalesce(
      jsonb_agg(to_jsonb(f) order by f.function_name, f.arguments),
      '[]'::jsonb
    )
    from function_snapshot f
  )
) as parket_security_snapshot
from parket_tables t
left join policy_snapshot p using (schema_name, table_name)
left join grant_snapshot g using (schema_name, table_name)
left join index_snapshot i using (schema_name, table_name);
