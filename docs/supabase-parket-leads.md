# Supabase-лиды Паркет36

Дата обновления документа: 2026-07-10.

Документ фиксирует схему публичной формы `/zayavka/`, требования безопасности и порядок проверки Edge Function.

Фактическое production-состояние вынесено в `docs/supabase-production-status-2026-07-10.md`.

## Проект и endpoint

- Supabase project id: `ofewxuqfjhamgerwzull`.
- Project URL: `https://ofewxuqfjhamgerwzull.supabase.co`.
- Edge Function: `parket-public-lead`.
- Endpoint: `https://ofewxuqfjhamgerwzull.supabase.co/functions/v1/parket-public-lead`.
- `verify_jwt`: `false`, потому что заявка отправляется с публичного сайта без авторизации, а функция сама проверяет origin, payload, rate limit и honeypot.

Публичный сайт не должен содержать service role key, health-токен, соль IP-хэша или секреты уведомлений. Запись в БД проходит только через Edge Function.

Изменение исходника в GitHub не обновляет развёрнутую Edge Function автоматически. После изменений в `supabase/functions/parket-public-lead/index.ts` нужен отдельный деплой в Supabase.

## Текущий production-статус

На 2026-07-10:

- проект имеет статус `ACTIVE_HEALTHY`;
- Edge Function `parket-public-lead` активна, но остаётся в версии `1`;
- актуальный исходник из `main` ещё не развёрнут;
- `parket_leads` и `parket_public_lead_audit` пусты;
- retention-миграция применена и проверена;
- Telegram и email подготовлены в исходнике, но не включены без secrets и деплоя.

Подробности и порядок production-деплоя: `docs/supabase-production-status-2026-07-10.md`.

## Файлы сайта

- `js/main.js` собирает payload формы, отправляет его в Edge Function и оставляет fallback через копирование текста.
- `js/lead-reliability.js` добавляет timeout, одну повторную попытку и honeypot-поля.
- `zayavka/index.html` и главная страница содержат публичную форму оценки.
- `/politika/` используется как ссылка на согласие с обработкой контактных данных.
- `docs/lead-endpoint-test-mode.md` описывает secrets и безопасную проверку endpoint.
- `docs/lead-notifications.md` описывает Telegram и email.
- `docs/lead-retention.md` описывает preview и ручную очистку.

## Обязательные production-настройки

- `SUPABASE_URL`.
- Secret/service role key, доступный только Edge Function.
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
- `accepted`, `reason`, `payload_summary` — результат обработки и доставки уведомлений.

## RLS и доступ

RLS включён на обеих таблицах.

Для ролей `anon` и `authenticated` действуют restrictive-политики:

- `parket_leads_no_public_direct_access`: `using false`, `with check false`;
- `parket_public_lead_audit_no_public_direct_access`: `using false`, `with check false`.

Прямые table privileges для публичных ролей не выдаются. Права на таблицы используются только внутри Edge Function через secret/service role key.

## Антиспам и надёжность актуального исходника

- Максимальный размер JSON: 25 000 байт.
- Honeypot-поля: `website` и `company`.
- Не более 30 любых попыток за 15 минут на один IP-хэш.
- Не более 6 принятых заявок за 15 минут на один IP-хэш.
- Одинаковый `request_id` не создаёт вторую заявку при retry.
- Фронтенд прекращает зависший запрос через 12 секунд и выполняет не более одной повторной попытки.
- При сбое backend текст обращения остаётся доступным для ручной отправки.
- Уведомления отправляются только после сохранения заявки и не могут отменить успешную запись.

Эти возможности относятся к актуальному исходнику. Они начнут работать в production только после настройки secrets и деплоя новой версии Edge Function.

## Безопасный тестовый режим

Payload:

```json
{"test_mode":true}
```

Обязательный заголовок:

```text
x-parket-health-token: <секрет>
```

Тестовый режим выполняет read-only проверку доступа к обеим таблицам и полноты конфигурации уведомлений. Он не создаёт заявку, audit-запись, Telegram-сообщение или письмо.

## Retention

В production применена миграция `20260710155135_add_parket_lead_retention_helpers`.

Она добавляет:

- `parket_retention_preview` — read-only подсчёт строк;
- `parket_apply_retention` — явную ручную очистку.

Функции доступны только `service_role`, не имеют автоматического расписания и не позволяют удалять статусы `new` или `in_progress`.

## Что проверять после деплоя функции

1. Функция получила новую версию и остаётся `ACTIVE`.
2. Production secrets настроены до деплоя.
3. Без health-токена тестовый режим возвращает отказ.
4. С правильным токеном обе таблицы имеют `ok: true`.
5. Настроенные каналы уведомлений имеют статус `configured`.
6. На сайте и в логах нет публичных secrets Supabase.
7. Публичные роли не получили прямой доступ к таблицам.
8. Реальная тестовая заявка создаёт одну строку в `parket_leads` и одну принятую audit-запись.
9. Фактически приходит Telegram-сообщение или email.
10. Повтор с тем же `request_id` не создаёт дубль.
11. При сбое Supabase форма сохраняет fallback-копирование текста.

## Следующие улучшения

- Настроить production secrets и развернуть актуальную Edge Function.
- Выполнить защищённый healthcheck и одну контролируемую реальную заявку.
- Добавить браузерный end-to-end тест формы.
- Добавить защищённый административный просмотр заявок.
- Добавить журнал смены статуса заявки.
- После накопления трафика проверить индексы и реальные причины отказов.
- Отдельно разбирать advisors по `nav_*`, `nav_v2_*` и Auth: они относятся к общему Supabase-проекту, а не только к Паркет36.
