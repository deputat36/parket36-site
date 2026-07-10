# Retention заявок и audit-данных Паркет36

SQL: `supabase/sql/parket_lead_retention.sql`.

Инструмент не создаёт расписание и не выбирает срок хранения автоматически. Даты отсечения и статусы задаются явно при каждом запуске.

## Что можно удалять

Audit-таблица:

- строки `parket_public_lead_audit` старше указанной даты.

Таблица заявок:

- только записи старше указанной даты;
- только статусы `done`, `spam` и `archived`.

Статусы `new` и `in_progress` функция удалить не позволяет.

## Почему нет срока по умолчанию

Срок хранения зависит от фактического процесса работы, политики обработки персональных данных и юридического решения владельца. Репозиторий предоставляет безопасный механизм, но не придумывает этот срок.

## Установка функций

Выполнить файл:

```text
supabase/sql/parket_lead_retention.sql
```

Функции доступны только `service_role`. Публичным ролям `anon` и `authenticated` доступ отозван.

## Шаг 1. Preview

Сначала посмотреть, сколько строк попадёт под очистку:

```sql
select *
from public.parket_retention_preview(
  p_audit_before => timestamptz '2026-04-01 00:00:00+00',
  p_lead_before => timestamptz '2025-07-01 00:00:00+00',
  p_lead_statuses => array['spam', 'archived']::text[]
);
```

Даты в примере не являются рекомендацией по сроку хранения. Перед использованием их нужно заменить на утверждённые значения.

## Шаг 2. Дополнительная ручная проверка

Перед удалением проверить сами записи:

```sql
select id, request_id, created_at, status, service, location
from public.parket_leads
where created_at < timestamptz '2025-07-01 00:00:00+00'
  and status = any(array['spam', 'archived']::text[])
order by created_at;
```

Для audit-таблицы:

```sql
select id, request_id, created_at, accepted, reason
from public.parket_public_lead_audit
where created_at < timestamptz '2026-04-01 00:00:00+00'
order by created_at;
```

## Шаг 3. Применение

После проверки выполнить очистку с теми же датами и статусами:

```sql
select *
from public.parket_apply_retention(
  p_audit_before => timestamptz '2026-04-01 00:00:00+00',
  p_lead_before => timestamptz '2025-07-01 00:00:00+00',
  p_lead_statuses => array['spam', 'archived']::text[]
);
```

Функция возвращает количество удалённых audit-строк и заявок.

## Защитные ограничения

- обе даты обязательны;
- даты должны находиться в прошлом;
- список статусов не может быть пустым;
- разрешены только `done`, `spam`, `archived`;
- автоматический `pg_cron` не создаётся;
- функции не доступны публичным ролям;
- перед destructive-функцией предусмотрен read-only preview.

## Что нужно утвердить отдельно

- срок хранения audit-данных;
- срок хранения контактных данных заявок;
- какие завершённые статусы можно удалять;
- требуется ли предварительный экспорт или резервная копия;
- будет ли очистка запускаться вручную или по расписанию.

До утверждения этих правил применять destructive-функцию нельзя.
