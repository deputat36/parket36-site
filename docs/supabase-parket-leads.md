# Supabase-лиды Паркет36

Дата обновления документа: 2026-07-10.

Документ фиксирует схему публичной формы `/zayavka/`, требования безопасности и порядок проверки Edge Function.

## Проект и endpoint

- Supabase project id: `ofewxuqfjhamgerwzull`.
- Project URL: `https://ofewxuqfjhamgerwzull.supabase.co`.
- Edge Function: `parket-public-lead`.
- Endpoint: `https://ofewxuqfjhamgerwzull.supabase.co/functions/v1/parket-public-lead`.
- `verify_jwt`: `false`, потому что заявка отправляется с публичного сайта без авторизации.

Публичный сайт не должен содержать service role key, health-токен, соль IP-хэша или другие секреты. Запись в БД проходит только через Edge Function.

Изменение исходника в GitHub не обновляет развёрнутую Edge Function автоматически. После изменений в `supabase/functions/parket-public-lead/index.ts` нужен отдельный деплой в Supabase.

## Файлы сайта

- `js/main.js` собирает payload формы, отправляет его в Edge Function и оставляет fallback через копирование текста.
- `js/lead-reliability.js` добавляет timeout, одну повторную попытку и honeypot-поля.
- `zayavka/index.html` и главная страница содержат публичную форму оценки.
- `/politika/` используется как ссылка на согласие с обработкой контактных данных.
- `docs/lead-endpoint-test-mode.md` описывает секреты и безопасную проверку endpoint.

## Обязательные production-настройки

- `SUPABASE_URL`.
- Service role secret.
- `PARKET_IP_HASH_SALT` — непубличная случайная соль.
- `PARKET_HEALTHCHECK_TOKEN` — отдельный токен тестового режима.
- `PARKET_PUBLIC_ALLOWED_ORIGINS` — при необходимости явный список разрешённых origin.

Без `PARKET_IP_HASH_SALT` новая версия функции возвращает `ip_hash_salt_required` и не принимает заявку. Флаг `PARKET_ALLOW_UNSALTED_IP_HASH=true` разрешён только для локальной разработки.

## Таблицы

### `public.parket_leads`

Назначение: заявки с публичной формы оценки пола.

Ключевые поля:

- `request_id` — idempotency key и защита от дублей;
- `created_at` — дата создания;
- `status` — `new`, `in_progress`, `done`, `spam`, `archived`;
- `service`, `location`, `area`, `photos`, `video`, `task`, `callback_time` — данные формы;
- `contact` — контакт клиента, содержит персональные данные;
- `page`, `attribution`, `metadata`, `user_agent` — технический и рекламный контекст.

### `public.parket_public_lead_audit`

Назначение: аудит публичных отправок и мягкий антиспам.

Ключевые поля:

- `request_id` — связь с попыткой отправки;
- `created_at` — дата попытки;
- `origin` — источник запроса;
- `ip_hash` — SHA-256 hash с непубличной солью, не сырой IP;
- `user_agent` — браузер/устройство;
- `accepted`, `reason`, `payload_summary` — результат обработки.

## RLS и доступ

RLS включён на обеих таблицах.

Для ролей `anon` и `authenticated` действуют restrictive-политики:

- `parket_leads_no_public_direct_access`: `using false`, `with check false`;
- `parket_public_lead_audit_no_public_direct_access`: `using false`, `with check false`.

Прямые table privileges для публичных ролей не выдаются. Права на таблицы используются только внутри Edge Function через service role.

## Антиспам и надёжность

- Максимальный размер JSON: 25 000 байт.
- Honeypot-поля: `website` и `company`.
- Не более 30 любых попыток за 15 минут на один IP-хэш.
- Не более 6 принятых заявок за 15 минут на один IP-хэш.
- Одинаковый `request_id` не создаёт вторую заявку при retry.
- Фронтенд прекращает зависший запрос через 12 секунд и выполняет не более одной повторной попытки.
- При сбое backend текст обращения остаётся доступным для ручной отправки.

## Безопасный тестовый режим

Payload:

```json
{"test_mode":true}
```

Обязательный заголовок:

```text
x-parket-health-token: <секрет>
```

Тестовый режим выполняет read-only проверку доступа к обеим таблицам. Он не создаёт строку в `parket_leads` и не добавляет запись в audit-таблицу.

## Что проверять после деплоя функции

1. Функция остаётся активной.
2. Production secrets настроены.
3. Без health-токена тестовый режим возвращает отказ.
4. С правильным токеном обе таблицы имеют `ok: true`.
5. На сайте нет публичных секретов Supabase.
6. Публичные роли не получили прямой доступ к таблицам.
7. Реальная тестовая заявка создаёт одну строку в `parket_leads` и одну принятую audit-запись.
8. Повтор с тем же `request_id` не создаёт дубль.
9. При сбое Supabase форма сохраняет fallback-копирование текста.

## Следующие улучшения

- Добавить retention SQL для автоматического удаления старых audit-записей и заявок по утверждённому сроку хранения.
- Подключить уведомление Ивану о новой заявке через Telegram или email.
- Добавить защищённый административный просмотр заявок.
- Добавить журнал смены статуса заявки.
- После накопления трафика проверить индексы и реальные причины отказов.
- Отдельно разбирать advisors по `nav_*`, `nav_v2_*` и Auth: они относятся к общему Supabase-проекту, а не только к Паркет36.
