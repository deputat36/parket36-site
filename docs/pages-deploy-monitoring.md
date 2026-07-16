# Мониторинг GitHub Pages deploy

## Назначение

Workflow `.github/workflows/pages-deploy-monitor.yml` отслеживает итог каждого завершённого `Deploy GitHub Pages` и поддерживает одно issue при повторяющемся отказе публикации.

Он не заменяет `Live site health`:

- Pages deploy monitor отвечает на вопрос, завершилась ли сама публикация GitHub Actions;
- live-health после успешного deploy проверяет DNS, HTTPS, публичные файлы, собранную главную и точный deployment manifest.

## Когда запускается

Монитор запускается только событием `workflow_run` после завершения `Deploy GitHub Pages`.

Планового и ручного запуска нет. Источником данных служит завершившийся workflow run:

- полный commit SHA;
- run ID Pages deploy;
- conclusion исходного workflow.

Checkout выполняется по `github.event.workflow_run.head_sha`.

## Поведение при отказе

Failure-like conclusions:

- `failure`;
- `cancelled`;
- `timed_out`;
- `action_required`;
- `startup_failure`;
- `stale`.

Первый единичный отказ не создаёт issue. Красный `Deploy GitHub Pages` уже остаётся основным немедленным сигналом.

Если два завершённых Pages deploy подряд имеют failure-like conclusion, создаётся одно issue:

`[monitoring] GitHub Pages deploy failure`

При следующих отказах новое issue и новые комментарии не создаются. Тело существующей задачи обновляется на месте и содержит только:

- время проверки;
- полный SHA;
- текущий и предыдущий conclusion;
- ссылку на Pages deploy;
- ссылку на workflow мониторинга.

Логи, artifacts, secrets и содержимое сайта в issue не копируются.

## Восстановление

Первый успешный Pages deploy после открытия monitoring issue:

1. добавляет один recovery-комментарий;
2. фиксирует успешный SHA и ссылки на оба workflow run;
3. закрывает issue со `state_reason: completed`.

Успешный deploy без открытого monitoring issue не создаёт комментариев или задач.

Conclusions `neutral` и `skipped` не открывают и не закрывают issue. Неизвестное значение обрабатывается fail-closed как ошибка manager-скрипта.

## Защита от ложных задач

`tools/manage_pages_deploy_issue.py`:

- требует полный 40-символьный SHA;
- требует цифровые run ID;
- принимает только известные conclusions;
- проверяет предыдущий завершённый run именно workflow `pages.yml`;
- ищет открытое issue по точному заголовку;
- обновляет одно существующее issue вместо создания потока комментариев;
- не скрывает ошибку GitHub API.

## Права

Workflow использует только:

- `contents: read` — checkout исходника manager по проверяемому SHA;
- `actions: read` — чтение предыдущего завершённого Pages run;
- `issues: write` — создание, обновление и закрытие monitoring issue.

`permissions: write-all` и `continue-on-error` запрещены CI-контрактом.

## Проверка без сети

```bash
python tools/manage_pages_deploy_issue.py --self-test
python tools/check_pages_deploy_monitoring.py
```

Self-test не обращается к GitHub и проверяет:

- правило двух последовательных отказов;
- отсутствие issue после единичного отказа;
- содержимое failure и recovery сообщений;
- валидацию SHA, run ID и conclusion.

## Ограничения

Монитор не повторяет deploy, не меняет Pages settings, не публикует сайт и не исправляет причину отказа.

При созданном issue нужно открыть ссылку на последний `Deploy GitHub Pages`, определить упавший job и исправить код или инфраструктурный сбой отдельным PR. После следующего успешного deploy issue закроется автоматически.
