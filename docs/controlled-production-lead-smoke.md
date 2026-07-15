# Контролируемая production-заявка

Workflow `.github/workflows/controlled-lead-smoke.yml` имеет два режима:

- `validate-only` по умолчанию — проверяет наличие обязательных GitHub Actions secrets и гарантированно не создаёт production-заявку;
- `operation=send` — после успешной проверки и approval environment `production` отправляет ровно одну реальную техническую заявку в `parket-public-lead`, а затем проверяет её наличие в `parket_leads` и принятую запись в `parket_public_lead_audit` через отдельную защищённую функцию `parket-lead-verify`.

Режим `send` — не обычный healthcheck: запуск действительно создаёт заявку, учитывается rate limit и при настроенном канале отправляет реальное Telegram/email-уведомление.

## Когда запускать

`validate-only` можно запускать заранее, чтобы получить безопасный отчёт о наличии `PARKET_SMOKE_CONTACT` и `PARKET_HEALTHCHECK_TOKEN`. Он не требует approval environment `production` и не вызывает публичную Edge Function.

`operation=send` разрешён только после того, как:

1. ручной workflow `Deploy production lead function` завершился успешно;
2. публичный CORS preflight зелёный;
3. защищённый production healthcheck зелёный;
4. `parket-public-lead` и `parket-lead-verify` развёрнуты из актуального `main`;
5. Иван предупреждён о техническом уведомлении;
6. подготовлен специальный контакт для проверки;
7. `validate-only` сформировал PASS для обоих GitHub secrets.

Не запускать `operation=send` многократно подряд. Каждая проверка создаёт реальную строку лида и audit-запись и расходует лимит production endpoint.

## GitHub secrets

В `Settings → Secrets and variables → Actions` должны быть настроены:

- `PARKET_SMOKE_CONTACT` — имя и реальный тестовый номер с 10–15 цифрами;
- `PARKET_HEALTHCHECK_TOKEN` — то же значение, что используется функциями в Supabase.

Контакт нельзя передавать как workflow input. Он хранится только в GitHub secret.

Readiness-checker получает только boolean-флаги `configured/missing`. Он не читает значение, длину, hash или часть secret. Рабочий workflow и итоговый smoke artifact также не выводят значение контакта или health-токена. В техническом smoke-отчёте показывается только количество цифр в контакте.

## Как проверить готовность без заявки

1. Открыть `Actions → Controlled production lead smoke`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Оставить `operation = validate-only`.
5. Поле подтверждения оставить пустым.
6. Запустить workflow.
7. Скачать artifact `controlled-lead-smoke-secret-readiness`.

Artifact содержит только имена двух secrets и статусы `PASS/FAIL`, `configured/missing`. Реальная заявка в этом режиме не создаётся, approval environment `production` не запрашивается.

## Как отправить одну контролируемую заявку

1. Открыть `Actions → Controlled production lead smoke`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Выбрать `operation = send`.
5. Ввести точную фразу:

```text
SEND_CONTROLLED_LEAD
```

6. Выбрать ожидаемое состояние уведомления:
   - `sent` — должен быть настроен рабочий Telegram или email;
   - `disabled` — каналы осознанно отключены;
   - `any` — допускается `sent` или `disabled`, но не `partial_failure`.
7. Дождаться успешного validate-job.
8. Подтвердить environment `production`, если в GitHub настроен required reviewer.

После approval workflow повторно проверяет оба GitHub secrets и сохраняет artifact `controlled-lead-smoke-final-secret-readiness`. Реальная заявка создаётся только после PASS этой повторной проверки.

## Какая заявка создаётся

Workflow формирует уникальный `request_id` с префиксом `smoke-` и отправляет:

- услугу `Контролируемая проверка production`;
- задачу с явным указанием не обрабатывать её как клиентскую;
- время связи `Не перезванивать — техническая проверка`;
- UTM `github / controlled_smoke / production_lead_verification`;
- контакт из `PARKET_SMOKE_CONTACT`.

Контакт нужен, потому что production backend применяет реальную серверную проверку номера телефона. Использовать вымышленный или чужой номер нельзя.

## Что проверяется

`tools/run_controlled_lead_smoke.py` проверяет ответ публичной функции:

- HTTP 200;
- `ok: true`;
- совпадение `request_id`;
- наличие `lead_id`;
- отсутствие признака duplicate;
- состояние `notification`;
- соответствие выбранному ожиданию уведомления.

Затем вызывается `parket-lead-verify` с `x-parket-health-token`. Verifier возвращает только технические признаки:

- строка с этим `request_id` найдена в `parket_leads`;
- принятая audit-запись найдена в `parket_public_lead_audit`.

Verifier не возвращает контакт, задачу, местоположение, текст уведомления или другие данные заявки.

## Artifacts

До создания заявки используются два безопасных readiness-отчёта:

```text
controlled-lead-smoke-secret-readiness
controlled-lead-smoke-final-secret-readiness
```

Они содержат только имена `PARKET_SMOKE_CONTACT`, `PARKET_HEALTHCHECK_TOKEN` и boolean-статусы наличия. Значения, длины и hashes secrets в отчёты не попадают.

После фактического `operation=send` технический отчёт сохраняется как:

```text
controlled-lead-smoke
```

Он содержит:

- `request_id`;
- ожидаемое и фактическое состояние уведомления;
- количество цифр в тестовом контакте;
- технические результаты ответа и двух таблиц.

Значение контакта и health-токен в artifact не попадают.

## Что остаётся проверить вручную

Даже зелёный workflow не доказывает, что Иван увидел сообщение. После PASS необходимо:

1. попросить Ивана подтвердить фактическое получение Telegram/email;
2. сверить request ID из artifact с уведомлением;
3. убедиться, что тестовая заявка не обрабатывается как обращение клиента;
4. оставить подтверждение в issue #373;
5. только после этого закрыть issue #373.

Workflow при техническом PASS добавляет комментарий в issue #373, но намеренно не закрывает его.

## Защита verifier

`parket-lead-verify`:

- имеет `verify_jwt = false`, поскольку вызывается без пользовательской Supabase-сессии;
- принимает только POST и OPTIONS;
- разрешает только `https://parket36.ru` и `https://www.parket36.ru`;
- требует точный `x-parket-health-token`;
- валидирует request ID;
- читает только факт наличия строк;
- не возвращает персональные данные.

## Локальные проверки

```bash
python tools/check_controlled_smoke_github_secrets.py --self-test
python tools/run_controlled_lead_smoke.py --self-test
python tools/check_controlled_lead_smoke.py
deno test supabase/functions/parket-lead-verify/request-id_test.ts
deno check supabase/functions/parket-lead-verify/index.ts
python tools/run_quality_checks.py
```

Локально не запускать реальный smoke без осознанной необходимости: `operation=send` создаст настоящую production-заявку.
