# Production lead endpoint health

Workflow `.github/workflows/lead-endpoint-health.yml` ежедневно и вручную проверяет production Edge Function `parket-public-lead` в защищённом тестовом режиме.

## Что проверяется

Запрос отправляет JSON:

```json
{"test_mode": true}
```

и секретный заголовок `x-parket-health-token`. Функция должна подтвердить:

- наличие service role secret;
- наличие `PARKET_IP_HASH_SALT`;
- доступ к таблице `parket_leads`;
- доступ к таблице `parket_public_lead_audit`;
- целостность конфигурации Telegram-уведомлений;
- целостность конфигурации email-уведомлений.

Тестовый режим не создаёт заявку и не добавляет строку в audit-таблицу.

## Как определяется endpoint

`tools/check_production_lead_endpoint.py` читает значение `PARKET_LEAD_ENDPOINT` непосредственно из `js/main.js`. Это не позволяет мониторингу и публичной форме незаметно использовать разные адреса.

Проверка требует HTTPS и точный путь `/functions/v1/parket-public-lead`.

## Настройка GitHub secret

В репозитории открыть:

`Settings → Secrets and variables → Actions → New repository secret`

Создать secret:

```text
PARKET_HEALTHCHECK_TOKEN
```

Значение должно совпадать с secret `PARKET_HEALTHCHECK_TOKEN` в проекте Supabase. Сам токен нельзя сохранять в репозитории, HTML, JavaScript, документации или workflow-логах.

## Поведение без secret

Пока GitHub secret отсутствует:

- workflow не отправляет запрос к Edge Function;
- создаётся artifact `production-lead-endpoint-health` со статусом `NOT CONFIGURED`;
- workflow не создаёт monitoring issue;
- существующий issue о реальном сбое не закрывается.

Это позволяет слить инфраструктуру мониторинга до ручной настройки production secrets.

## Поведение при ошибке

Если токен настроен, но endpoint не отвечает HTTP 200 или хотя бы одна обязательная проверка возвращает `ok: false`:

1. workflow становится красным;
2. отчёт сохраняется как artifact `production-lead-endpoint-health`;
3. создаётся или дополняется один issue `[monitoring] production lead endpoint failure`;
4. токен в отчёт и issue не попадает.

Типовые ответы:

- `healthcheck_not_configured` — токен не настроен в Supabase;
- `healthcheck_forbidden` — GitHub и Supabase используют разные токены;
- `ip_hash_salt_required` — отсутствует production-соль;
- ошибка `parket_leads` или `parket_public_lead_audit` — функция не может прочитать обязательную таблицу;
- частично заполненные параметры Telegram или email — канал уведомлений настроен не полностью.

После успешного защищённого healthcheck открытый monitoring issue закрывается автоматически.

## Ручной запуск

Открыть:

`Actions → Production lead endpoint health → Run workflow`

Проверять нужно artifact `production-lead-endpoint-health`. В нём отображаются только публичный endpoint, HTTP-статус и безопасные результаты проверок.

## Локальная проверка структуры

```bash
python tools/check_production_lead_endpoint.py --self-test
python tools/manage_lead_endpoint_issue.py --self-test
python tools/check_lead_endpoint_monitoring.py
```

Реальный защищённый запрос локально:

```bash
PARKET_HEALTHCHECK_TOKEN="..." \
python tools/check_production_lead_endpoint.py \
  --report lead-endpoint-health.md \
  --require-token
```

Не публиковать созданный локальный файл, если в него вручную добавлялись дополнительные диагностические данные.

## Ограничения

- healthcheck подтверждает функцию, таблицы и конфигурацию каналов, но не отправляет реальное уведомление Ивану;
- после первого зелёного healthcheck всё равно нужна одна контролируемая реальная заявка;
- исходник Edge Function в GitHub не развёртывается в Supabase автоматически;
- production deploy и secrets настраиваются вручную до первой полноценной проверки.
