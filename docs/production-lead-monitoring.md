# Production lead endpoint health

Workflow `.github/workflows/lead-endpoint-health.yml` ежедневно и вручную проверяет production Edge Function `parket-public-lead` двумя независимыми способами:

1. публичный CORS preflight без secret;
2. защищённый `test_mode` при наличии `PARKET_HEALTHCHECK_TOKEN`.

Обе проверки не создают заявку.

## Публичный CORS preflight

`tools/check_public_lead_preflight.py` отправляет только HTTP `OPTIONS` на endpoint из `data/site.json`.

Запрос передаёт:

- `Origin: https://parket36.ru`;
- `Access-Control-Request-Method: POST`;
- `Access-Control-Request-Headers: content-type`.

Проверяются:

- HTTP 200 или 204;
- точный `Access-Control-Allow-Origin: https://parket36.ru`;
- наличие `POST` и `OPTIONS` в `Access-Control-Allow-Methods`;
- наличие `content-type` в `Access-Control-Allow-Headers`;
- `Vary: Origin`.

Эта проверка не отправляет данные формы, не использует токен, не обращается к таблицам и не создаёт заявку. Она подтверждает только публичную маршрутизацию Edge Function и браузерный CORS-контракт.

Отчёт сохраняется как artifact:

```text
public-lead-endpoint-preflight
```

При ошибке создаётся или обновляется отдельный issue:

```text
[monitoring] public lead preflight failure
```

После успешного preflight этот issue закрывается автоматически независимо от состояния защищённого healthcheck.

## Защищённый healthcheck

Если GitHub secret `PARKET_HEALTHCHECK_TOKEN` настроен, workflow отправляет JSON:

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

Отчёт сохраняется как artifact:

```text
production-lead-endpoint-health
```

При ошибке создаётся или обновляется отдельный issue:

```text
[monitoring] production lead endpoint failure
```

После успешного защищённого healthcheck закрывается только этот protected issue. Public preflight issue ведётся отдельно.

## Как определяется endpoint

Источник правды — поле `lead_endpoint` в `data/site.json`.

Команда:

```bash
python tools/site_settings.py --write
```

синхронизирует значение с константой `PARKET_LEAD_ENDPOINT` в `js/main.js` и с эксплуатационными инструкциями. Общий quality gate запускает `python tools/site_settings.py --check` и блокирует публикацию при любом расхождении.

Публичный checker читает `lead_endpoint` напрямую из общего конфига. Защищённый checker намеренно читает адрес из `js/main.js`, то есть проверяет endpoint, которым фактически пользуется браузерная форма. Статический guardrail требует полного совпадения обоих источников.

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

- публичный CORS preflight всё равно выполняется;
- artifact `public-lead-endpoint-preflight` содержит фактический результат публичной проверки;
- защищённый запрос не выполняется;
- artifact `production-lead-endpoint-health` имеет статус `NOT CONFIGURED`;
- protected issue не создаётся и не закрывается;
- public preflight issue создаётся или закрывается по фактическому OPTIONS-ответу.

Таким образом можно контролировать доступность endpoint до ручной настройки production secrets, не создавая ложного впечатления, что таблицы и уведомления уже готовы.

## Поведение при ошибке

Публичная ошибка означает, что браузер, вероятно, не сможет вызвать Edge Function с `parket36.ru`. Типовые причины:

- endpoint не развёрнут или недоступен;
- неправильный URL;
- production origin отсутствует в CORS;
- не разрешён метод `POST`;
- не разрешён заголовок `content-type`;
- отсутствует `Vary: Origin`.

Защищённая ошибка означает, что функция доступна, но production-контур не готов полностью. Типовые ответы:

- `healthcheck_not_configured` — токен не настроен в Supabase;
- `healthcheck_forbidden` — GitHub и Supabase используют разные токены;
- `ip_hash_salt_required` — отсутствует production-соль;
- ошибка `parket_leads` или `parket_public_lead_audit` — функция не может прочитать обязательную таблицу;
- частично заполненные параметры Telegram или email — канал уведомлений настроен не полностью.

В обоих случаях workflow становится красным после загрузки отчётов и обновления соответствующего monitoring issue.

## Ручной запуск

Открыть:

`Actions → Production lead endpoint health → Run workflow`

Проверять оба artifacts:

1. `public-lead-endpoint-preflight` — публичная маршрутизация и CORS;
2. `production-lead-endpoint-health` — таблицы, secrets и уведомления.

Зелёный preflight без настроенного protected healthcheck не подтверждает готовность принимать и доставлять заявки.

## Локальная проверка структуры

```bash
python tools/site_settings.py --check
python tools/check_public_lead_preflight.py --self-test
python tools/check_production_lead_endpoint.py --self-test
python tools/manage_lead_endpoint_issue.py --self-test
python tools/check_lead_endpoint_monitoring.py
```

Реальный публичный preflight локально:

```bash
python tools/check_public_lead_preflight.py \
  --report lead-endpoint-preflight.md
```

Реальный защищённый запрос локально:

```bash
PARKET_HEALTHCHECK_TOKEN="..." \
python tools/check_production_lead_endpoint.py \
  --report lead-endpoint-health.md \
  --require-token
```

Не публиковать созданные локальные отчёты, если в них вручную добавлялись дополнительные диагностические данные.

## Смена Supabase endpoint

1. Изменить только `lead_endpoint` в `data/site.json`.
2. Выполнить `python tools/site_settings.py --write`.
3. Проверить diff `js/main.js` и двух инструкций.
4. Запустить общий quality gate.
5. После публикации вручную запустить `Production lead endpoint health`.
6. Проверить оба artifacts.

Не редактировать URL отдельно в `js/main.js`: такой diff будет остановлен shared-settings проверкой.

## Ограничения

- public preflight подтверждает маршрутизацию и CORS, но не проверяет Supabase tables или уведомления;
- protected healthcheck подтверждает функцию, таблицы и конфигурацию каналов, но не отправляет реальное уведомление Ивану;
- после первого зелёного protected healthcheck всё равно нужна одна контролируемая реальная заявка;
- исходник Edge Function в GitHub не развёртывается в Supabase автоматически;
- production deploy и secrets настраиваются вручную до первой полноценной проверки.
