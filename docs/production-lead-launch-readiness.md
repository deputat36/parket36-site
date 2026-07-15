# Единая проверка готовности production-заявок

Workflow `.github/workflows/production-lead-launch-readiness.yml` собирает один безопасный отчёт о готовности полного production-цикла заявок.

Он не развёртывает Edge Functions, не вызывает защищённый healthcheck и не создаёт заявку.

## Что проверяется

Один ручной запуск проверяет пять независимых уровней:

1. исходники обеих Edge Functions: Deno unit-тесты и `deno check`;
2. GitHub secrets для deploy: `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_ID`, `PARKET_HEALTHCHECK_TOKEN`;
3. remote Supabase secrets и выбранную политику уведомлений;
4. GitHub secrets для controlled smoke: `PARKET_SMOKE_CONTACT`, `PARKET_HEALTHCHECK_TOKEN`;
5. текущий публичный CORS-контракт production endpoint через HTTP `OPTIONS`.

Публичный preflight не передаёт secret, не отправляет данные формы и не создаёт строку лида.

## Как запустить

1. Открыть `Actions → Production lead launch readiness`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Выбрать политику уведомлений:
   - `require-configured` — до deploy должен быть полностью настроен Telegram или email;
   - `allow-disabled` — отсутствие канала допускается осознанно.
5. Запустить workflow.
6. Скачать artifact `production-lead-launch-readiness`.
7. Открыть issue #373: один служебный комментарий с последним итоговым уровнем обновляется автоматически.

Environment `production` и required reviewer для этой проверки не используются.

## Привязка к исходному коммиту

После сборки summary workflow запускает:

```bash
python tools/stamp_production_lead_launch_readiness.py \
  --commit-sha "$GITHUB_SHA" \
  --report production-lead-launch-readiness.md
```

В итоговом файле и управляемом комментарии issue #373 появляются строки:

```text
Source commit: `<40-символьный SHA>`
Snapshot validity: this result applies only to this exact commit; rerun after any change to `main`.
```

Readiness-снимок действителен только для указанного коммита. После любого нового merge или прямого изменения `main` необходимо повторить readiness после любого изменения `main`, даже если предыдущий уровень был зелёным.

Stamper:

- принимает только точный 40-символьный lowercase hexadecimal SHA;
- не принимает короткий SHA или произвольный ref;
- при повторном запуске заменяет прежний SHA и не создаёт дубликаты;
- требует наличие заголовка и `Readiness level`;
- не читает secrets и не изменяет компонентные отчёты.

Если stamping завершился ошибкой:

- artifact всё равно загружается для диагностики;
- issue #373 не обновляется неоднозначным снимком;
- workflow становится красным независимо от readiness level.

## Уровни готовности

### BLOCKED

Нельзя переходить к deploy. Возможные причины:

- не прошли тесты или type-check;
- отсутствуют GitHub deploy secrets;
- remote Supabase readiness не выполнен;
- обязательные Supabase secrets отсутствуют;
- канал уведомлений настроен частично;
- выбранная политика уведомлений не соблюдена.

### DEPLOY_READY

Deploy prerequisites готовы, но controlled smoke пока заблокирован отсутствующим `PARKET_SMOKE_CONTACT` или health-токеном в GitHub.

### LAUNCH_READY

Исходники, deploy secrets, remote Supabase secrets и controlled smoke secrets готовы.

Текущий production preflight может показывать `DRIFT`. Это ожидаемо до deploy актуального `main` и не блокирует подготовку.

Следующий порядок:

1. `Deploy production lead function` с `operation=validate-only`;
2. отдельный запуск с `operation=deploy`;
3. public preflight и protected healthcheck;
4. `Controlled production lead smoke` с `operation=validate-only`;
5. один запуск `operation=send`;
6. подтверждение фактического уведомления Иваном.

### PRODUCTION_CONTRACT_CURRENT

Readiness прошёл, а production endpoint уже объявляет актуальный CORS-контракт с `x-parket-health-token`.

Этот статус ещё не доказывает доступность таблиц, protected healthcheck, доставку уведомления или controlled real lead.

## Что находится в artifact

```text
production-lead-launch-readiness.md
edge-github-secret-readiness.md
edge-deploy-readiness.md
controlled-lead-smoke-secret-readiness.md
lead-endpoint-preflight.md
```

Временный `remote-secret-names.json` удаляется до загрузки artifact.

## Синхронизация с issue #373

После успешного stamping workflow запускает `tools/manage_production_lead_launch_readiness.py`.

Скрипт поддерживает один автоматически управляемый комментарий:

- первый запуск создаёт комментарий с уникальным marker;
- следующие запуски обновляют тот же комментарий;
- повторяющиеся комментарии не создаются;
- в issue публикуется только единый summary, `Source commit` и ссылка на workflow run;
- component reports остаются только в Actions artifact;
- issue #373 не закрывается автоматически.

Сбой синхронизации не скрывает artifact и не меняет итог readiness workflow.

## Защита данных

Workflow:

- получает только boolean-флаги наличия health-токена и smoke-контакта;
- не передаёт значения `PARKET_HEALTHCHECK_TOKEN` и `PARKET_SMOKE_CONTACT`;
- использует Supabase access token только для чтения имён remote secrets;
- не загружает raw-ответ Supabase CLI;
- не выводит длины, hashes, digests, части значений или тестовый контакт;
- не содержит `supabase functions deploy`;
- не вызывает `tools/run_controlled_lead_smoke.py`;
- не копирует component reports в issue.

## Production drift

До первого актуального deploy endpoint может не объявлять `x-parket-health-token`.

Поэтому `DRIFT` отображается в summary, но не блокирует уровень `LAUNCH_READY`, если остальные prerequisites готовы. После deploy preflight должен стать `CURRENT`, а monitoring issue #375 — закрыться автоматически.

## Локальные проверки

```bash
python tools/build_production_lead_launch_readiness.py --self-test
python tools/stamp_production_lead_launch_readiness.py --self-test
python tools/manage_production_lead_launch_readiness.py --self-test
python tools/check_production_lead_launch_readiness.py
python tools/check_edge_github_secrets.py --self-test
python tools/check_controlled_smoke_github_secrets.py --self-test
python tools/check_edge_deploy_readiness.py --self-test
python tools/check_public_lead_preflight.py --self-test
python tools/run_quality_checks.py
```
