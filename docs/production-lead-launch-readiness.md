# Единая проверка готовности production-заявок

Workflow `.github/workflows/production-lead-launch-readiness.yml` собирает один безопасный отчёт о готовности полного production-цикла заявок.

Он не развёртывает Edge Functions, не вызывает защищённый healthcheck и не создаёт заявку.

## Что проверяется

Один ручной запуск проверяет пять независимых уровней:

1. исходники обеих Edge Functions:
   - Deno unit-тесты;
   - `deno check`;
2. GitHub secrets, необходимые для deploy:
   - `SUPABASE_ACCESS_TOKEN`;
   - `SUPABASE_PROJECT_ID`;
   - `PARKET_HEALTHCHECK_TOKEN`;
3. remote Supabase secrets и выбранную политику уведомлений;
4. GitHub secrets для controlled smoke:
   - `PARKET_SMOKE_CONTACT`;
   - `PARKET_HEALTHCHECK_TOKEN`;
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
6. Скачать artifact:

```text
production-lead-launch-readiness
```

7. Открыть issue #373: один служебный комментарий с последним итоговым уровнем и дальнейшими действиями обновляется автоматически после каждого запуска.

Environment `production` и required reviewer для этой проверки не используются.

## Уровни готовности

Итоговый файл `production-lead-launch-readiness.md` показывает один из четырёх уровней.

### BLOCKED

Нельзя переходить к deploy. Возможные причины:

- не прошли тесты или type-check;
- отсутствуют GitHub deploy secrets;
- remote Supabase readiness не выполнен или завершился ошибкой;
- обязательные Supabase secrets отсутствуют;
- канал уведомлений настроен частично;
- выбранная политика уведомлений не соблюдена.

### DEPLOY_READY

Deploy prerequisites готовы, но controlled smoke пока заблокирован отсутствующим `PARKET_SMOKE_CONTACT` или health-токеном в GitHub.

Функции технически можно разворачивать, но полный цикл запуска ещё нельзя завершить одной проверочной заявкой.

### LAUNCH_READY

Исходники, deploy secrets, remote Supabase secrets и controlled smoke secrets готовы.

Текущий production preflight может показывать `DRIFT`. Это ожидаемое состояние до deploy актуального `main` и не блокирует подготовку.

Следующий порядок:

1. `Deploy production lead function` с `operation=validate-only`;
2. отдельный запуск с `operation=deploy`;
3. public preflight и protected healthcheck;
4. `Controlled production lead smoke` с `operation=validate-only`;
5. один запуск `operation=send`;
6. подтверждение фактического уведомления Иваном.

### PRODUCTION_CONTRACT_CURRENT

Проверки готовности прошли, а публичный production endpoint уже объявляет актуальный CORS-контракт с `x-parket-health-token`.

Этот статус ещё не доказывает:

- доступность таблиц через service role;
- успешный protected healthcheck;
- фактическую доставку Telegram/email;
- прохождение controlled real lead.

## Что находится в artifact

Artifact содержит:

```text
production-lead-launch-readiness.md
edge-github-secret-readiness.md
edge-deploy-readiness.md
controlled-lead-smoke-secret-readiness.md
lead-endpoint-preflight.md
```

Если GitHub deploy secrets отсутствуют, remote Supabase check будет отмечен как `BLOCKED`, а файл `edge-deploy-readiness.md` может отсутствовать. Итоговый summary всё равно создаётся.

## Синхронизация с issue #373

После загрузки artifact workflow запускает `tools/manage_production_lead_launch_readiness.py`.

Скрипт поддерживает один автоматически управляемый комментарий в issue #373:

- первый запуск создаёт комментарий с уникальным служебным marker;
- следующие запуски находят этот комментарий и обновляют его через GitHub API;
- новые повторяющиеся комментарии не создаются;
- комментарий содержит только единый `production-lead-launch-readiness.md` summary и ссылку на workflow run;
- component reports не копируются в issue и остаются только в Actions artifact;
- сбой синхронизации issue не скрывает artifact и не меняет итог readiness workflow.

Комментарий не закрывает issue #373 и не подтверждает deploy, protected healthcheck или доставку уведомления. Он только фиксирует последнюю проверенную готовность и следующие действия.

Для этого workflow имеет минимальное дополнительное разрешение `issues: write`. Доступ к содержимому репозитория остаётся `contents: read`.

## Защита данных

Workflow:

- получает только boolean-флаги наличия health-токена и smoke-контакта;
- не передаёт значения `PARKET_HEALTHCHECK_TOKEN` и `PARKET_SMOKE_CONTACT` в команды;
- использует Supabase access token только для чтения имён remote secrets;
- удаляет временный `remote-secret-names.json` до загрузки artifact;
- не загружает raw-ответ Supabase CLI;
- не выводит длины, hashes, digests, части значений или тестовый контакт;
- не содержит `supabase functions deploy`;
- не вызывает `tools/run_controlled_lead_smoke.py`;
- публикует в issue только summary, который сам содержит явные safety markers;
- отказывается публиковать component или diagnostic reports вместо summary.

## Почему production drift не всегда делает workflow красным

До первого актуального deploy production endpoint ожидаемо может не объявлять `x-parket-health-token`.

Поэтому:

- `DRIFT` отображается в итоговом отчёте;
- preflight-компонент сохраняется для диагностики;
- при готовых prerequisites итоговый уровень становится `LAUNCH_READY`;
- workflow становится красным только при блокерах исходников, deploy readiness или controlled smoke readiness.

После deploy тот же preflight должен стать `CURRENT`, а автоматический monitoring issue #375 — закрыться.

## Локальные проверки

```bash
python tools/build_production_lead_launch_readiness.py --self-test
python tools/manage_production_lead_launch_readiness.py --self-test
python tools/check_production_lead_launch_readiness.py
python tools/check_edge_github_secrets.py --self-test
python tools/check_controlled_smoke_github_secrets.py --self-test
python tools/check_edge_deploy_readiness.py --self-test
python tools/check_public_lead_preflight.py --self-test
python tools/run_quality_checks.py
```
