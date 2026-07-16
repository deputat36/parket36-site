# Watchdog подтверждённого deploy

Workflow: `.github/workflows/verified-deploy-drift.yml`.

## Зачем нужен отдельный watchdog

`Deploy GitHub Pages` сообщает о явном сбое публикации. `Live site health` проверяет публичный домен и после полного post-deploy успеха обновляет в issue #308 единственный служебный комментарий `Последняя подтверждённая публикация parket36.ru`.

Остаётся отдельный отказоустойчивый сценарий: workflow может быть отключён, не запуститься или завершиться успешно, но не обновить ledger из-за временной ошибки GitHub API. В таком случае сам сайт может продолжать работать на старой версии, красного Pages deploy не будет, а обычный live monitoring без точного expected SHA не обязан заметить отставание от `main`.

Watchdog сравнивает:

- текущий `main` или точный `head_sha` завершившегося `Live site health`;
- полный SHA из единственного marker-комментария issue #308.

Совпадение означает, что текущая проверяемая версия уже подтверждена на `parket36.ru`. Несовпадение означает verified deploy drift.

## Когда запускается

Workflow запускается:

1. после каждого успешно завершённого `Live site health`;
2. ежедневно по расписанию;
3. вручную через `workflow_dispatch`.

После `workflow_run` проверяется именно `github.event.workflow_run.head_sha`. Это исключает гонку, если новый commit попал в `main` сразу после завершившегося live-health.

Ежедневный и ручной режим checkout выполняют из основной ветки и используют фактический `git rev-parse HEAD`.

Неуспешный `Live site health` не запускает job watchdog: его уже обслуживает `[monitoring] parket36.ru live health failure`.

## Что проверяется

`tools/check_verified_deploy_drift.py` требует:

- issue #308 существует, остаётся открытым и сохраняет точный заголовок дорожной карты;
- найден ровно один комментарий с marker `parket36-live-verification`;
- marker встречается в комментарии ровно один раз;
- строка `Опубликованный commit` содержит один полный 40-символьный SHA;
- ledger SHA совпадает с проверяемым SHA.

Отсутствующий, повреждённый или продублированный ledger обрабатывается fail-closed.

## Диагностический artifact

Каждый запуск сохраняет `verified-deploy-drift-report` с файлом `verified-deploy-drift-report.md` на 30 дней.

Отчёт содержит только:

- PASS или FAIL;
- время проверки;
- проверяемый SHA;
- ledger SHA либо `unavailable`;
- ссылку на issue #308;
- ссылку на workflow run;
- краткую причину результата.

Secrets, содержимое других комментариев, workflow logs и данные заявок в artifact не копируются.

## Monitoring issue

Первый единичный drift не создаёт issue: workflow сохраняет artifact и завершается ошибкой.

Если следующий завершённый запуск этого же watchdog также неуспешен, создаётся одна задача:

`[monitoring] verified deploy drift`

Следующие неуспешные запуски обновляют тело этой задачи на месте. Новые комментарии при каждом drift не создаются.

Первый успешный запуск после восстановления добавляет recovery-комментарий и закрывает issue с `state_reason: completed`.

Такой порог защищает от короткой задержки между merge, Pages deploy, live-health и обновлением ledger, но сохраняет долговечный сигнал при реальном отставании публикации.

## Связь с другими monitoring-контурами

- `[monitoring] GitHub Pages deploy failure` — два последовательных явных отказа Pages workflow;
- `[monitoring] parket36.ru live health failure` — повторный сбой DNS, HTTPS, публичных файлов, телефона, клиентского текста или deployment manifest;
- `[monitoring] verified deploy drift` — текущая проверяемая версия не совпадает с последним подтверждённым deploy;
- `[monitoring] IndexNow notification failure` — повторный сбой отправки URL после публикации.

Эти задачи не дублируют друг друга: каждая фиксирует отдельную границу отказа.

## Права и безопасность

Workflow использует:

- `contents: read` — checkout точной версии;
- `actions: read` — определение предыдущего результата watchdog;
- `issues: write` — создание, обновление и закрытие одного monitoring issue.

Watchdog не развёртывает сайт, не повторяет Pages deploy, не меняет DNS или Pages settings, не обращается к Supabase и не отправляет реальные заявки.

Ошибки issue-manager не подменяют фактический результат проверки: служебные шаги используют `continue-on-error`, а отдельный финальный шаг сохраняет красный статус при drift.

## Офлайн-проверки

```bash
python tools/check_verified_deploy_drift.py --self-test
python tools/manage_verified_deploy_drift_issue.py --self-test
python tools/check_verified_deploy_drift_workflow.py
```

Боевой запуск checker требует GitHub Actions environment и доступ к issue #308. Локальный self-test не выполняет сетевые запросы.
