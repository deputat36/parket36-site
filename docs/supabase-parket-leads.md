# Supabase-лиды Паркет36

Дата проверки: 2026-07-02.

Документ фиксирует текущую схему публичной формы `/zayavka/`, чтобы при следующих правках сайта не потерять связь с Supabase и не ослабить безопасность таблиц с контактными данными.

## Проект и endpoint

- Supabase project id: `ofewxuqfjhamgerwzull`
- Project URL: `https://ofewxuqfjhamgerwzull.supabase.co`
- Edge Function для публичной формы: `parket-public-lead`
- Endpoint в коде сайта: `https://ofewxuqfjhamgerwzull.supabase.co/functions/v1/parket-public-lead`
- `verify_jwt`: `false`, потому что заявка отправляется с публичного сайта без авторизации.
- Статус Edge Function на 2026-07-02: `ACTIVE`, версия `1`.

Публичный сайт не должен содержать `service_role` key или другие секреты. Запись в БД должна проходить только через Edge Function.

## Файлы сайта

- `js/main.js` собирает payload формы, отправляет его в Edge Function и оставляет fallback через копирование текста.
- `zayavka/index.html` содержит публичную форму оценки паркета по фото.
- `/politika/` используется как ссылка на согласие с обработкой контактных данных.

## Таблицы

### `public.parket_leads`

Назначение: заявки с публичной формы оценки пола.

Ключевые поля:

- `request_id` — idempotency key, уникальный идентификатор заявки.
- `created_at` — дата создания.
- `status` — `new`, `in_progress`, `done`, `spam`, `archived`.
- `service`, `location`, `area`, `photos`, `video`, `task`, `callback_time` — данные формы.
- `contact` — контакт клиента, содержит персональные данные.
- `page`, `attribution`, `metadata`, `user_agent` — технический и рекламный контекст.

На момент проверки строк: `0`.
Последняя заявка: нет данных.

### `public.parket_public_lead_audit`

Назначение: аудит публичных отправок формы и мягкий антиспам.

Ключевые поля:

- `request_id` — связь с попыткой отправки.
- `created_at` — дата попытки.
- `origin` — источник запроса.
- `ip_hash` — SHA-256 hash, не сырой IP.
- `user_agent` — браузер/устройство.
- `accepted`, `reason`, `payload_summary` — результат обработки.

На момент проверки строк: `0`.
Последняя попытка отправки: нет данных.

## RLS и доступ

RLS включён на обеих таблицах.

Для ролей `anon` и `authenticated` действуют restrictive-политики:

- `parket_leads_no_public_direct_access`: `using false`, `with check false`.
- `parket_public_lead_audit_no_public_direct_access`: `using false`, `with check false`.

Прямые table privileges для `anon` и `authenticated` не выданы. Права на таблицы есть у `service_role`.

Практический вывод: публичная форма не должна писать напрямую в таблицы через REST API. Любые изменения фронтенда должны сохранять отправку через Edge Function.

## Текущие advisors и логи

Security advisors по проекту показывают много предупреждений по `SECURITY DEFINER` функциям других модулей (`nav_*`, `nav_v2_*`) и предупреждение о выключенной leaked password protection в Auth.

По `parket_*` критичных security-предупреждений при проверке не выявлено.

Свежая проверка логов Edge Functions через Supabase connector не показала событий в доступном окне логов. При этом таблицы `parket_leads` и `parket_public_lead_audit` остаются пустыми, поэтому реальных успешных или отклонённых отправок формы пока не видно.

Performance advisors ранее показывали INFO по неиспользованным индексам `parket_*`:

- `parket_leads_created_at_idx`
- `parket_leads_status_created_at_idx`
- `parket_leads_attribution_gin_idx`
- `parket_public_lead_audit_created_at_idx`
- `parket_public_lead_audit_ip_hash_created_at_idx`
- `parket_public_lead_audit_request_id_idx`

Эти индексы не удалять автоматически: таблицы пока пустые, поэтому отсутствие использования ожидаемо. Решение об удалении возможно только после накопления реального трафика и проверки запросов.

## Что проверять после правок формы

1. Edge Function `parket-public-lead` остаётся активной.
2. На сайте нет публичных секретов Supabase.
3. Форма сохраняет fallback: если отправка в Supabase не прошла, текст заявки можно скопировать и отправить вручную.
4. `anon` и `authenticated` не получают прямой доступ к `parket_leads` и `parket_public_lead_audit`.
5. В `parket_leads` не сохраняются фото как файлы. Фото клиент отправляет отдельно, а форма фиксирует только статус готовности фото.
6. При изменении payload нужно сверить поля с Edge Function и таблицей `parket_leads`.
7. После реального теста формы проверить, что появилась строка в `parket_leads` и соответствующая запись в `parket_public_lead_audit`.

## Что можно улучшить позже

- Провести ручной тест публичной формы на боевом сайте и убедиться, что заявка доходит до Supabase.
- Добавить админский просмотр заявок для Ивана без раскрытия публичного доступа к таблицам.
- Добавить уведомление о новой заявке в Telegram или email через Edge Function.
- Добавить отдельный статус обработки заявки и короткий журнал действий мастера.
- После появления трафика проверить использование индексов и реальные причины отказов в `parket_public_lead_audit`.
- Отдельно разобрать security advisors по `nav_*`, `nav_v2_*` и Auth, потому что они относятся к общему Supabase-проекту, а не только к сайту Паркет36.
