# Безопасная проверка Edge Function заявок

Функция: `supabase/functions/parket-public-lead/index.ts`.

Endpoint: `parket-public-lead`.

## Обязательные секреты production

Перед развёртыванием новой версии функции должны быть настроены:

- `PARKET_IP_HASH_SALT` — случайная непубличная строка для хэширования IP;
- `PARKET_HEALTHCHECK_TOKEN` — отдельный токен для безопасного тестового режима;
- стандартные `SUPABASE_URL` и service role secret.

Рекомендуется использовать для `PARKET_IP_HASH_SALT` и `PARKET_HEALTHCHECK_TOKEN` разные случайные значения длиной не менее 32 символов.

## Защита соли

В production функция не принимает заявки, если `PARKET_IP_HASH_SALT` отсутствует. Ответ:

```json
{"ok":false,"error":"ip_hash_salt_required"}
```

Для локальной разработки без production-секретов допускается только явный флаг:

```text
PARKET_ALLOW_UNSALTED_IP_HASH=true
```

Этот флаг нельзя использовать в production.

## Тестовый режим

Тестовый запрос проверяет:

- наличие service role secret;
- наличие соли IP-хэша;
- доступ функции к `parket_leads`;
- доступ функции к `parket_public_lead_audit`.

Тестовый режим не создаёт заявку и не добавляет строку в audit-таблицу.

Пример запроса:

```bash
curl -X POST \
  "https://ofewxuqfjhamgerwzull.supabase.co/functions/v1/parket-public-lead" \
  -H "Content-Type: application/json" \
  -H "x-parket-health-token: $PARKET_HEALTHCHECK_TOKEN" \
  -d '{"test_mode":true}'
```

При успешной проверке функция возвращает HTTP 200 и объект `checks`.

Если токен не настроен, возвращается `healthcheck_not_configured`. Если токен неверный — `healthcheck_forbidden`.

## Порядок развёртывания

1. Создать случайные значения соли и health-токена.
2. Сохранить их в secrets проекта Supabase.
3. Развернуть новую версию `parket-public-lead`.
4. Выполнить тестовый запрос.
5. Убедиться, что обе таблицы имеют статус `ok: true`.
6. После этого выполнить одну реальную тестовую заявку через публичную форму.
7. Проверить появление одной строки в `parket_leads` и соответствующей записи в audit-таблице.

## Ограничения

- Health-токен нельзя помещать в HTML, JavaScript, README-примеры с реальным значением или публичные логи.
- Тестовый режим не проверяет доставку уведомления Ивану — уведомления подключаются отдельным этапом.
- Изменения исходника в GitHub не обновляют уже развёрнутую Edge Function автоматически.
