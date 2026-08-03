# Production security snapshot — Паркет36

Проверено: 3 августа 2026 года.

Supabase-проект: `ofewxuqfjhamgerwzull`.

Проверка выполнялась только чтением. Схема, данные, secrets, Auth и Edge Functions не изменялись. Production-заявки не создавались.

## Итог

Объекты Паркет36 в базе закрыты корректно:

- таблицы `public.parket_leads` и `public.parket_public_lead_audit` существуют;
- на обеих таблицах включён RLS;
- для `anon` и `authenticated` действует явная deny-all policy;
- прямых табличных прав у `anon` и `authenticated` нет;
- полный доступ есть только у `postgres` и `service_role`;
- `parket_retention_preview` и `parket_apply_retention` имеют `SECURITY DEFINER`, но `EXECUTE` выдан только `postgres` и `service_role`;
- на момент проверки в `parket_leads` и `parket_public_lead_audit` было 0 строк.

Критических security/performance advisory, относящихся именно к объектам Паркет36, не обнаружено.

## Индексы

Advisor отметил несколько индексов Паркет36 как неиспользованные:

- `parket_leads_attribution_gin_idx`;
- `parket_public_lead_audit_ip_hash_created_at_idx`;
- `parket_public_lead_audit_request_id_idx`.

Удалять их сейчас нельзя. Таблицы пусты, поэтому отсутствие сканирований ожидаемо. Эти индексы нужны для атрибуции, rate limit, поиска request ID и диагностики после появления реальных заявок.

## Что не относится к Паркет36

Общий Supabase-проект используется несколькими системами. Advisor также показал предупреждения по таблицам и RPC `nav_*`, `leader_*`, `newbuild_*`, а также глобальную настройку защиты паролей.

Эти замечания нельзя исправлять из проекта Паркет36 без отдельной проверки владельцев соседних систем: изменение RPC grants, RLS, индексов или Auth может повлиять на CRM, «Навигатор сделок» и другие приложения.

## Оставшийся production-блокер

Edge Function `parket-public-lead` по-прежнему развёрнута как version 1 и отстаёт от исходника в `main`.

До deploy обязательны:

1. `PARKET_IP_HASH_SALT` в Supabase secrets;
2. `PARKET_HEALTHCHECK_TOKEN` в Supabase и GitHub Actions secrets;
3. выбранный канал уведомлений либо осознанное решение использовать `notification: disabled`;
4. отдельное разрешение на одну контролируемую production-заявку после deploy.

Без этих данных текущую функцию развёртывать нельзя: актуальный код намеренно работает fail-closed при отсутствии соли.

## Повторная проверка

Использовать `supabase/verify-parket-security.sql`.

Скрипт:

- выполняет только `SELECT`;
- не вызывает Edge Function;
- не создаёт лид или audit row;
- показывает RLS, policies, grants, ACL retention-функций, число строк и статистику индексов.

Повторять проверку после:

- миграций таблиц Паркет36;
- изменения RLS или grants;
- изменения retention-функций;
- deploy новой Edge Function;
- появления первых реальных заявок.
