# Безопасный deploy `parket-public-lead`

Workflow `.github/workflows/deploy-lead-function.yml` предназначен только для ручного развёртывания production Edge Function после настройки обязательных secrets.

Он не запускается по `push`, `pull_request` или расписанию.

## Что нужно настроить в GitHub

В `Settings → Secrets and variables → Actions` добавить:

- `SUPABASE_ACCESS_TOKEN` — персональный access token Supabase для CLI;
- `SUPABASE_PROJECT_ID` — project ref `ofewxuqfjhamgerwzull`;
- `PARKET_HEALTHCHECK_TOKEN` — то же значение, которое сохранено как Edge Function secret в Supabase.

В `Settings → Environments` рекомендуется создать environment `production` и добавить required reviewer. Workflow уже привязан к этому environment, но обязательное ручное подтверждение на уровне GitHub настраивается в интерфейсе репозитория.

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

Частичная конфигурация любого канала всегда блокирует deploy. Отсутствие обоих каналов блокирует deploy при политике `require-configured`, но допускается при осознанном выборе `allow-disabled`.

Значения secrets не читаются и не записываются в artifacts. Workflow получает через `supabase secrets list` только имена и проверяет комплектность.

## Публичная конфигурация функции

Файл `supabase/config.toml` содержит:

```toml
[functions.parket-public-lead]
verify_jwt = false
```

Дополнительно команда deploy использует `--no-verify-jwt`. Двойная фиксация нужна, потому что форма вызывается публичным браузером без пользовательской Supabase-сессии, а собственная защита реализована внутри функции: origin policy, payload validation, honeypot, rate limit и защищённый healthcheck.

## Как запустить

1. Открыть `Actions → Deploy production lead function`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Ввести точную фразу:

```text
DEPLOY_PARKET_PUBLIC_LEAD
```

5. Выбрать политику уведомлений:
   - `require-configured` — deploy разрешён только при полном Telegram или email-канале;
   - `allow-disabled` — разрешить функцию с ответом `notification: disabled`, если это принято осознанно.
6. Подтвердить запуск и approval environment `production`, если required reviewer настроен.

## Что выполняется до deploy

Workflow:

1. запрещает запуск не из `main`;
2. проверяет точную подтверждающую фразу;
3. проверяет наличие трёх GitHub secrets без вывода значений;
4. устанавливает Supabase CLI через официальный `supabase/setup-cli`;
5. запускает четыре Deno unit-теста и `deno check`;
6. получает список имён remote secrets;
7. сверяет `SUPABASE_PROJECT_ID` с endpoint из `data/site.json`;
8. проверяет `supabase/config.toml` и обязательные файлы функции;
9. формирует artifact `edge-deploy-readiness`;
10. останавливается до deploy при любом несоответствии.

## Deploy и проверка после него

Команда развёртывания:

```bash
supabase functions deploy parket-public-lead \
  --project-ref "$SUPABASE_PROJECT_ID" \
  --use-api \
  --no-verify-jwt
```

После успешного deploy workflow обязательно запускает:

- публичный CORS preflight;
- защищённый `test_mode` healthcheck.

Отчёты сохраняются в artifact `edge-deploy-post-checks`.

При сбое обновляются независимые monitoring issues:

- `[monitoring] public lead preflight failure`;
- `[monitoring] production lead endpoint failure`.

При двух зелёных проверках workflow оставляет комментарий в issue #373. Issue не закрывается автоматически, потому что после технического deploy всё равно требуется одна контролируемая реальная заявка.

## Что проверить после зелёного workflow

1. Выполнить одну заявку с известным тестовым номером и пометкой «контролируемая проверка».
2. Проверить запись в `parket_leads`.
3. Проверить audit row в `parket_public_lead_audit`.
4. Проверить `notification` в ответе функции.
5. Подтвердить фактическое получение Telegram или email Иваном.
6. Только после этого закрыть issue #373.

## Локальные проверки

```bash
python tools/check_edge_deploy_readiness.py --self-test
python tools/check_workflows.py
python tools/run_quality_checks.py
```

## Ограничения

- workflow не создаёт и не меняет Supabase secrets;
- workflow не подтверждает фактическое чтение уведомления Иваном;
- `allow-disabled` не рекомендуется для постоянной работы, потому что заявка сохранится, но Иван может не узнать о ней автоматически;
- raw-вывод `supabase secrets list` удаляется до загрузки artifacts;
- deploy выполняется только вручную и только из текущего `main`.
