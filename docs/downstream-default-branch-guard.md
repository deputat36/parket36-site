# Защита downstream workflow основной веткой

## Назначение

`Deploy GitHub Pages` публикует production-сайт только из default branch. Downstream-workflow должны независимо повторять это ограничение, потому что завершённый ручной Pages workflow со skipped jobs всё равно может создать событие `workflow_run`.

Защищены:

- `.github/workflows/live-site-health.yml`;
- `.github/workflows/indexnow.yml`.

## Live site health

Job выполняется только в двух случаях:

1. плановый или ручной запуск выполняется из `github.event.repository.default_branch`;
2. событие `workflow_run` относится к успешному `Deploy GitHub Pages`, а `workflow_run.head_branch` совпадает с default branch.

Checkout использует:

- точный `workflow_run.head_sha` после production deploy;
- default branch для планового и ручного запуска.

Ручной запуск workflow из feature-ветки остаётся `skipped`. Он не может:

- создать ложный live-health failure;
- обновить или закрыть monitoring issue;
- изменить ledger последнего подтверждённого deploy;
- закрыть issue переключения Pages.

## IndexNow

Автоматическая отправка выполняется только после успешного Pages workflow основной ветки.

Ручной `workflow_dispatch` разрешён только из default branch. Checkout в ручном режиме также принудительно использует default branch.

Feature-ветка не может отправить поисковым системам:

- sitemap непубликованной сборки;
- URL экспериментальной страницы;
- IndexNow payload, не соответствующий production-сайту.

## Независимые уровни защиты

Ограничение применяется независимо на трёх уровнях:

1. Pages build/deploy допускает только default branch;
2. Pages failure monitor фильтрует `workflow_run.head_branch`;
3. Live site health и IndexNow повторно фильтруют source branch перед любым production-действием.

Даже если один workflow будет изменён ошибочно, соседний guard не должен автоматически доверять его результату.

## CI-контракт

Обязательные проверки:

```bash
python tools/check_live_health_workflow.py
python tools/check_indexnow_workflow.py
```

Они требуют:

- сравнение `github.ref_name` с `github.event.repository.default_branch`;
- сравнение `github.event.workflow_run.head_branch` с default branch;
- checkout default branch в ручном и плановом режиме;
- точный checkout опубликованного SHA после production deploy;
- отсутствие старого fallback `|| github.sha`;
- отсутствие прежних условий, допускавших любой успешный Pages workflow.

## Границы

Изменение не публикует сайт, не отправляет заявку, не вызывает Supabase и не меняет Pages settings. IndexNow отправляется только при штатном запуске основной ветки.