# Безопасный deploy production Edge Functions

Workflow `.github/workflows/deploy-lead-function.yml` вручную проверяет и при отдельном подтверждении развёртывает две production-функции:

- `parket-public-lead` — принимает публичные заявки;
- `parket-lead-verify` — по защищённому request ID подтверждает наличие строки лида и принятой audit-записи.

Он не запускается по `push`, `pull_request` или расписанию.

## Два режима operation

Поле `operation` предлагает два варианта:

- `validate-only` — режим по умолчанию;
- `deploy` — реальное развёртывание после успешной проверки.

`validate-only` выполняет полный readiness-job, формирует artifact `edge-deploy-readiness` и ничего не развёртывает. Этот job не использует environment `production`, поэтому безопасную проверку можно выполнить без deployment approval.

`deploy` сначала проходит тот же readiness-job. Затем запускается отдельный deploy-job, который:

- зависит от успешного readiness-job;
- использует environment `production`;
- ожидает required reviewer, если он настроен;
- повторно проверяет подтверждение, GitHub secrets и remote Supabase secrets после approval;
- только после этого выполняет deploy.

Такой повторный контроль исключает ситуацию, когда конфигурация изменилась между первой проверкой и ручным approval.

## Что нужно настроить в GitHub

В `Settings → Secrets and variables → Actions` добавить:

- `SUPABASE_ACCESS_TOKEN` — персональный access token Supabase для CLI;
- `SUPABASE_PROJECT_ID` — project ref `ofewxuqfjhamgerwzull`;
- `PARKET_HEALTHCHECK_TOKEN` — то же значение, которое сохранено как Edge Function secret в Supabase.

В `Settings → Environments` создать environment `production` и добавить required reviewer. Он применяется только к deploy-job. Режим `validate-only` не выполняет этот job.

## Что должно быть настроено в Supabase

Обязательные Edge Function secrets:

- `PARKET_IP_HASH_SALT`;
- `PARKET_HEALTHCHECK_TOKEN`.

Уведомления можно настроить одним или двумя каналами.

Полный Telegram-канал:

- `PARKET_TELEGRAM_BOT_TOKEN`;
- `PARKET_TELEGRAM_CHAT_ID`.

Полный email-канал:

- `PARKET_RESEND_API_KEY`;
- `PARKET_EMAIL_FROM`;
- `PARKET_EMAIL_TO`.

Частичная конфигурация любого канала всегда блокирует readiness и deploy. Отсутствие обоих каналов блокирует проверку при политике `require-configured`, но допускается при осознанном выборе `allow-disabled`.

Значения secrets не читаются и не записываются в artifacts. Workflow получает через `supabase secrets list` только имена и проверяет комплектность.

## Публичная конфигурация функций

Файл `supabase/config.toml` содержит:

```toml
[functions.parket-public-lead]
verify_jwt = false

[functions.parket-lead-verify]
verify_jwt = false
```

Дополнительно обе команды deploy используют `--no-verify-jwt`.

`parket-public-lead` вызывается публичным браузером без пользовательской Supabase-сессии. Его собственная защита включает origin policy, payload validation, honeypot, rate limit и защищённый healthcheck.

`parket-lead-verify` также вызывается без пользовательской сессии, но принимает только точный `x-parket-health-token`, разрешает два production origin и возвращает только факт наличия строк — без контакта, задачи и других персональных данных.

## Сначала проверить readiness

1. Открыть `Actions → Deploy production lead function`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Оставить `operation = validate-only`.
5. Поле подтверждения оставить пустым.
6. Выбрать политику уведомлений:
   - `require-configured` — требуется полный Telegram или email-канал;
   - `allow-disabled` — допускается осознанный ответ `notification: disabled`.
7. Запустить workflow.
8. Скачать artifact `edge-deploy-readiness`.

При PASS функции не меняются. При FAIL отчёт показывает отсутствующие GitHub/Supabase-настройки без значений secrets.

## Запустить deploy

После зелёного `validate-only` повторно открыть workflow и выбрать:

- `operation = deploy`;
- подтверждение `DEPLOY_PARKET_PUBLIC_LEAD`;
- ту же политику уведомлений, которая была проверена ранее.

После readiness-job GitHub запустит deploy-job через environment `production`. После required reviewer workflow повторно получает список remote secrets и формирует artifact `edge-deploy-final-readiness`.

Deploy не начнётся, если финальная проверка после approval стала красной.

## Что проверяется до deploy

Readiness-job:

1. запрещает запуск не из `main`;
2. проверяет допустимое значение `operation`;
3. требует точную подтверждающую фразу только для `deploy`;
4. проверяет наличие трёх GitHub secrets без вывода значений;
5. устанавливает Supabase CLI через официальный `supabase/setup-cli`;
6. запускает unit-тесты и `deno check` для обеих функций;
7. получает список имён remote secrets;
8. сверяет `SUPABASE_PROJECT_ID` с endpoint из `data/site.json`;
9. проверяет оба раздела `supabase/config.toml` и обязательные файлы функций;
10. формирует artifact `edge-deploy-readiness`.

Deploy-job после approval повторяет проверки GitHub secrets и remote secrets и формирует `edge-deploy-final-readiness`.

## Deploy и проверка после него

Сначала разворачивается verifier:

```bash
supabase functions deploy parket-lead-verify \
  --project-ref "$SUPABASE_PROJECT_ID" \
  --use-api \
  --no-verify-jwt
```

Только после его успеха разворачивается публичная функция:

```bash
supabase functions deploy parket-public-lead \
  --project-ref "$SUPABASE_PROJECT_ID" \
  --use-api \
  --no-verify-jwt
```

После двух успешных deploy workflow обязательно запускает:

- публичный CORS preflight;
- защищённый `test_mode` healthcheck.

Отчёты сохраняются в artifact `edge-deploy-post-checks`.

При сбое обновляются независимые monitoring issues:

- `[monitoring] public lead preflight failure`;
- `[monitoring] production lead endpoint failure`.

При двух зелёных проверках workflow оставляет комментарий в issue #373. Issue не закрывается автоматически, потому что после технического deploy всё равно требуется одна контролируемая реальная заявка.

## Контролируемая реальная заявка

После зелёного deploy использовать отдельный workflow `Controlled production lead smoke`, описанный в `docs/controlled-production-lead-smoke.md`.

Он:

1. создаёт одну техническую заявку с уникальным request ID;
2. проверяет ответ `parket-public-lead` и состояние `notification`;
3. вызывает `parket-lead-verify` с health-токеном;
4. подтверждает строку в `parket_leads`;
5. подтверждает принятую запись в `parket_public_lead_audit`;
6. не выводит тестовый контакт в artifact.

После технического PASS всё равно нужно подтвердить фактическое получение Telegram/email Иваном. Только после этого закрывается issue #373.

## Локальные проверки

```bash
python tools/check_edge_deploy_readiness.py --self-test
python tools/check_edge_deploy_workflow.py
python tools/run_controlled_lead_smoke.py --self-test
python tools/check_controlled_lead_smoke.py
deno test supabase/functions/parket-lead-verify/request-id_test.ts
deno check supabase/functions/parket-lead-verify/index.ts
python tools/check_workflows.py
python tools/run_quality_checks.py
```

## Ограничения

- workflow не создаёт и не меняет Supabase secrets;
- `validate-only` требует настроенные GitHub secrets и доступ к Supabase, но ничего не развёртывает;
- workflow не подтверждает фактическое чтение уведомления Иваном;
- `allow-disabled` не рекомендуется для постоянной работы, потому что заявка сохранится, но Иван может не узнать о ней автоматически;
- raw-вывод `supabase secrets list` удаляется до загрузки artifacts;
- deploy выполняется только вручную, только из текущего `main` и только после отдельного approval;
- controlled smoke создаёт реальную запись и не должен запускаться многократно.
