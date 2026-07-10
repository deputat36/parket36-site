# Production-статус Supabase Паркет36

Дата проверки: 2026-07-10.

Проект: `ofewxuqfjhamgerwzull`.

Этот документ фиксирует фактическое состояние production, а не только содержимое репозитория.

## Состояние проекта

- Supabase project status: `ACTIVE_HEALTHY`.
- Регион: `eu-west-1`.
- PostgreSQL: `17.6.1.121`.
- Edge Function `parket-public-lead`: `ACTIVE`.
- Развёрнутая версия Edge Function: `1`.
- `verify_jwt`: `false`, как требуется для публичной формы с собственной проверкой origin и payload.

## Важное расхождение

Исходник `supabase/functions/parket-public-lead/index.ts` в GitHub новее production-версии.

В production-версии 1 ещё нет:

- общего лимита всех попыток;
- обязательной соли IP-хэша;
- защищённого `test_mode`;
- Telegram-уведомлений;
- email-уведомлений через Resend;
- расширенных audit-статусов доставки уведомлений.

Поэтому наличие кода в `main` нельзя считать завершённым production-деплоем.

## Таблицы Паркет36

На момент проверки:

- `public.parket_leads`: RLS включён, строк `0`;
- `public.parket_public_lead_audit`: RLS включён, строк `0`.

Логи Edge Functions за доступные последние 24 часа не содержали событий по форме Паркет36.

## Retention уже применён

В production применена миграция:

```text
20260710155135_add_parket_lead_retention_helpers
```

Установлены функции:

- `public.parket_retention_preview`;
- `public.parket_apply_retention`.

Проверено:

- `anon` не имеет права `EXECUTE`;
- `authenticated` не имеет права `EXECUTE`;
- `service_role` имеет право `EXECUTE`;
- preview на пустых таблицах вернул `audit_rows = 0`, `lead_rows = 0`;
- автоматическое расписание очистки не создавалось.

## Что нужно настроить перед деплоем Edge Function

Обязательные production secrets:

- `PARKET_IP_HASH_SALT`;
- `PARKET_HEALTHCHECK_TOKEN`.

Для Telegram:

- `PARKET_TELEGRAM_BOT_TOKEN`;
- `PARKET_TELEGRAM_CHAT_ID`.

Для email через Resend:

- `PARKET_RESEND_API_KEY`;
- `PARKET_EMAIL_FROM`;
- `PARKET_EMAIL_TO`;
- `PARKET_EMAIL_SUBJECT` — необязательно.

Secrets задаются в Supabase Dashboard в разделе Edge Functions → Secrets или через Supabase CLI. Реальные значения нельзя хранить в GitHub, issue, HTML, JavaScript или workflow-логах.

После изменения secrets повторный деплой функции не требуется: переменные становятся доступны функции отдельно от версии исходника.

## Безопасный порядок production-деплоя

1. Создать разные случайные значения длиной не менее 32 символов для соли и health-токена.
2. Добавить `PARKET_IP_HASH_SALT` и `PARKET_HEALTHCHECK_TOKEN` в Edge Function Secrets.
3. Добавить полностью настроенный Telegram или email-канал либо оставить оба канала полностью выключенными.
4. Не использовать `PARKET_ALLOW_UNSALTED_IP_HASH=true` в production.
5. Развернуть актуальный `supabase/functions/parket-public-lead/index.ts` с `verify_jwt=false`.
6. Убедиться, что новая версия имеет статус `ACTIVE`.
7. Выполнить защищённый запрос `{"test_mode":true}` с health-токеном.
8. Проверить `ok: true` для обеих таблиц и настроенных каналов.
9. Отправить одну контролируемую реальную заявку через публичную форму.
10. Проверить одну строку в `parket_leads`, принятую audit-запись и фактическое уведомление.
11. Повторить запрос с тем же `request_id` и убедиться, что дубль не создан.
12. Проверить fallback формы при искусственно недоступном endpoint.

## Почему функция пока не развёрнута

Новая версия блокирует приём заявок без `PARKET_IP_HASH_SALT`. Доступный коннектор умеет развернуть Edge Function, но не умеет безопасно создать production secrets. Деплой до настройки соли создал бы риск отказа формы с ошибкой `ip_hash_salt_required`.

До появления secrets безопаснее оставить активной версию 1, чем развернуть защищённый исходник в неполной конфигурации.

## Advisors после миграции

Retention-функции не добавили новых предупреждений Supabase Advisors.

Оставшиеся security и performance warnings относятся к другим модулям общего проекта, главным образом `nav_*`, `nav_v2_*`, Auth и старым общим таблицам. Их нельзя исправлять в рамках Паркет36 без отдельного аудита зависимостей этих приложений.
