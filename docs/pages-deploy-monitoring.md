# Мониторинг GitHub Pages deploy

## Назначение

Workflow `.github/workflows/pages-deploy-monitor.yml` отслеживает итог каждого завершённого `Deploy GitHub Pages` только для основной ветки репозитория и поддерживает одно issue при повторяющемся отказе публикации.

Он не заменяет `Live site health`:

- Pages deploy monitor отвечает на вопрос, завершилась ли сама публикация GitHub Actions;
- live-health после успешного deploy проверяет DNS, HTTPS, публичные файлы, собранную главную и точный deployment manifest.

## Защита production-публикации

`Deploy GitHub Pages` запускается автоматически только при push в основную ветку. `workflow_dispatch` остаётся доступен для ручной диагностики, но job `build` имеет отдельный guard:

`github.ref_name == github.event.repository.default_branch`

Поэтому ручной запуск feature-ветки не публикуется: build и зависимый от него deploy остаются пропущенными.

Pages monitor использует второй независимый guard:

`github.event.workflow_run.head_branch == github.event.repository.default_branch`

Даже если защита самого deploy будет случайно ослаблена, результат другой ветки не сможет открыть, обновить или закрыть production monitoring issue.

## Когда запускается

Монитор запускается только событием `workflow_run` после завершения `Deploy GitHub Pages`.

Планового и ручного запуска monitor нет. Источником данных служит завершившийся workflow run основной ветки:

- полный commit SHA;
- run ID Pages deploy;
- conclusion исходного workflow;
- `head_branch`;
- default branch репозитория.

Checkout выполняется по `github.event.workflow_run.head_sha` только после проверки ветки.

## Поведение при отказе

Failure-like conclusions:

- `failure`;
- `cancelled`;
- `timed_out`;
- `action_required`;
- `startup_failure`;
- `stale`.

Первый единичный отказ не создаёт issue. Красный `Deploy GitHub Pages` уже остаётся основным немедленным сигналом.

Если два завершённых Pages deploy основной ветки подряд имеют failure-like conclusion, создаётся одно issue:

`[monitoring] GitHub Pages deploy failure`

При следующих отказах новое issue и новые комментарии не создаются. Тело существующей задачи обновляется на месте и содержит только:

- время проверки;
- имя основной ветки;
- полный SHA;
- текущий и предыдущий conclusion;
- ссылку на Pages deploy;
- ссылку на workflow мониторинга.

Логи, artifacts, secrets и содержимое сайта в issue не копируются.

## Восстановление

Первый успешный Pages deploy основной ветки после открытия monitoring issue:

1. добавляет один recovery-комментарий;
2. фиксирует ветку, успешный SHA и ссылки на оба workflow run;
3. закрывает issue со `state_reason: completed`.

Успешный deploy без открытого monitoring issue не создаёт комментариев или задач. Успешный run другой ветки не участвует в recovery.

Conclusions `neutral` и `skipped` не открывают и не закрывают issue. Неизвестное значение обрабатывается fail-closed как ошибка manager-скрипта.

## Защита от ложных задач

`tools/manage_pages_deploy_issue.py`:

- требует полный 40-символьный SHA;
- требует цифровые run ID;
- принимает только известные conclusions;
- требует переменные `PAGES_DEPLOY_BRANCH` и `PAGES_DEFAULT_BRANCH`;
- прекращает работу, если проверяемая ветка не совпадает с default branch;
- запрашивает предыдущие workflow runs с API-фильтром `branch`;
- дополнительно проверяет `head_branch` каждого найденного run;
- проверяет предыдущий завершённый run именно workflow `pages.yml` и той же основной ветки;
- ищет открытое issue по точному заголовку;
- обновляет одно существующее issue вместо создания потока комментариев;
- не скрывает ошибку GitHub API.

## Права

Workflow использует только:

- `contents: read` — checkout исходника manager по проверяемому SHA;
- `actions: read` — чтение предыдущего завершённого Pages run основной ветки;
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
- валидацию SHA, run ID и conclusion;
- совпадение deploy/default branch;
- отказ для feature-ветки;
- URL истории workflow с encoded branch filter.

## Ограничения

Монитор не повторяет deploy, не меняет Pages settings, не публикует сайт и не исправляет причину отказа.

При созданном issue нужно открыть ссылку на последний `Deploy GitHub Pages`, определить упавший job и исправить код или инфраструктурный сбой отдельным PR. После следующего успешного deploy основной ветки issue закроется автоматически.
