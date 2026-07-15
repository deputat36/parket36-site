# Автоматическое устаревание production readiness

Readiness-снимок в issue #373 действителен только для точного `Source commit`, указанного в управляемом комментарии.

После изменения ветки `main` старый снимок нельзя использовать как разрешение на deploy, даже если его уровень был `LAUNCH_READY` или `PRODUCTION_CONTRACT_CURRENT`.

## Автоматическая пометка после push

Workflow `.github/workflows/production-lead-readiness-stale.yml` запускается только при `push` в `main`.

Он:

- не развёртывает Edge Functions;
- не вызывает protected healthcheck;
- не создаёт заявку;
- не читает GitHub или Supabase secrets проекта;
- использует только встроенный `github.token` с минимальными разрешениями `contents: read` и `issues: write`;
- ищет в issue #373 только комментарий с marker `parket36-production-lead-launch-readiness`;
- не создаёт новый readiness-комментарий;
- добавляет или обновляет один warning-блок `STALE` внутри найденного комментария;
- ничего не меняет, если управляемого комментария ещё нет.

Warning показывает:

- commit, для которого выполнялась последняя readiness-проверка;
- текущий SHA ветки `main`;
- ссылку на workflow run, который обнаружил устаревание;
- требование повторно запустить `Production lead launch readiness`.

Повторный запуск stale-workflow для того же SHA идемпотентен: второй warning не создаётся.

## Защита от гонки workflow

Одной push-пометки недостаточно, если readiness был запущен на старом `main`, а новый merge произошёл до завершения проверки.

Поэтому шаг `Update issue 373 readiness snapshot` выполняет две команды атомарно:

```bash
python tools/verify_production_lead_readiness_current_main.py \
  --report production-lead-launch-readiness.md
python tools/manage_production_lead_launch_readiness.py \
  --report production-lead-launch-readiness.md
```

Verifier:

1. извлекает единственный полный `Source commit` из stamped summary;
2. читает текущий `refs/heads/main` через GitHub API;
3. требует точного совпадения двух 40-символьных lowercase SHA;
4. останавливает шаг до вызова manager при любом расхождении.

Если `main` изменился во время readiness:

- artifact уже сохранён и остаётся доступным для диагностики;
- issue #373 не обновляется старым результатом;
- шаг `issue_snapshot` получает `failure`;
- финальный шаг делает workflow красным;
- нужно повторить readiness из актуального `main`.

## Жизненный цикл комментария

1. До первого ручного readiness управляемого комментария может не быть.
2. Первый успешный readiness создаёт комментарий с точным `Source commit`.
3. Новый push в `main` автоматически добавляет warning `STALE`.
4. Следующий успешный readiness для текущего `main` полностью заменяет комментарий свежим summary и удаляет warning.
5. Issue #373 остаётся открытым до deploy, protected healthcheck, controlled real lead и подтверждения доставки уведомления Иваном.

## Защита данных

Stale-workflow и current-main verifier не получают:

- `SUPABASE_ACCESS_TOKEN`;
- `PARKET_HEALTHCHECK_TOKEN`;
- `PARKET_SMOKE_CONTACT`;
- параметры Telegram или email;
- значения remote Supabase secrets;
- данные заявок.

В warning попадают только публичные commit SHA и ссылка на GitHub Actions run.

## Локальные проверки

```bash
python tools/mark_production_lead_readiness_stale.py --self-test
python tools/verify_production_lead_readiness_current_main.py --self-test
python tools/check_production_lead_readiness_staleness.py
python tools/run_quality_checks.py
```
