# Автоматическое уведомление IndexNow

## Назначение

Workflow `Notify IndexNow after deploy` сообщает поддерживающим протокол поисковым системам, что опубликованные URL Паркет36 готовы к повторному обходу.

Он запускается:

- автоматически после успешного workflow `Deploy GitHub Pages`;
- вручную через `workflow_dispatch`, если уведомление нужно повторить.

## Последовательность

1. Workflow получает SHA именно завершившейся публикации.
2. Checkout выполняется по этому SHA, а не по произвольному текущему состоянию `main`.
3. `tools/submit_indexnow.py --self-test` проверяет формирование payload и отчёта без сети.
4. `tools/submit_indexnow.py --check` сверяет:
   - `data/indexnow.json`;
   - ключ в корневом `.txt`-файле;
   - публикацию ключевого файла сборщиком;
   - домен и URL из sitemap;
   - ограничение до 10 000 URL.
5. `tools/manage_indexnow_issue.py --self-test` проверяет логику текста ошибки, восстановления и ограничение размера отчёта без обращения к GitHub API.
6. Скрипт проверяет живой ключ на `parket36.ru`. Для задержки CDN предусмотрено до шести попыток с интервалом 10 секунд.
7. После подтверждения ключа все URL текущего sitemap отправляются одним JSON POST в глобальный endpoint IndexNow.
8. Ответ `200` или `202` считается успешным приёмом уведомления.
9. Markdown-отчёт сохраняется как artifact `indexnow-report` на 30 дней и добавляется в Job Summary.
10. При повторном сбое обновляется одно monitoring issue; успешная отправка закрывает его автоматически.

## Поведение при ошибке

Отправка выполняется с `continue-on-error`, чтобы сначала сохранить диагностический отчёт и обновить monitoring issue. Затем отдельный шаг завершает job ошибкой.

Красный `Notify IndexNow after deploy` означает проблему уведомления поисковых систем. Он не отменяет и не откатывает уже завершившийся deploy GitHub Pages.

В отчёте фиксируются:

- опубликованный домен;
- endpoint;
- расположение ключа;
- количество URL sitemap;
- число попыток проверки живого ключа;
- HTTP-статус;
- краткая причина успеха или ошибки.

Значение самого ключа в отчёт и monitoring issue не выводится.

## Monitoring issue

Скрипт `tools/manage_indexnow_issue.py` обслуживает отдельную задачу:

```text
[monitoring] IndexNow notification failure
```

Порядок работы:

1. Первый единичный неуспешный запуск сохраняет красный статус и artifact, но issue не создаётся.
2. Если предыдущий завершённый запуск этого же workflow также был неуспешным, создаётся одно issue.
3. Следующие сбои добавляют комментарии с новым отчётом в уже открытую задачу.
4. Первый успешный запуск добавляет комментарий о восстановлении и закрывает issue со статусом `completed`.

В issue попадают только ссылка на Actions run и ограниченный фрагмент `indexnow-report.md`. Значение ключа не включается. Ошибка GitHub API при создании или закрытии issue не подменяет результат IndexNow: служебные шаги имеют `continue-on-error`, а основной workflow остаётся красным или зелёным по фактической отправке.

## Права workflow

Workflow использует минимальные разрешения:

- `contents: read` — checkout опубликованной ревизии;
- `actions: read` — определение результата предыдущего запуска;
- `issues: write` — создание, обновление и закрытие одного monitoring issue.

`permissions: write-all` и запись в содержимое репозитория не нужны.

## Ручная проверка без сети

```bash
python tools/submit_indexnow.py --self-test
python tools/submit_indexnow.py --check
python tools/manage_indexnow_issue.py --self-test
python tools/check_indexnow_workflow.py
```

## Ручная отправка

Команда выполняет реальную сетевую отправку:

```bash
python tools/submit_indexnow.py \
  --submit \
  --attempts 6 \
  --retry-delay 10 \
  --timeout 20 \
  --report indexnow-report.md
```

Обычно ручная отправка не нужна: после каждого успешного deploy срабатывает workflow.

Команды `manage_indexnow_issue.py failure` и `manage_indexnow_issue.py success` предназначены для GitHub Actions, поскольку требуют `GITHUB_TOKEN`, `GITHUB_REPOSITORY` и `GITHUB_RUN_ID`.

## Ограничения

Успешный ответ подтверждает, что IndexNow получил список URL. Это не гарантирует:

- немедленный обход;
- добавление страницы в индекс;
- рост позиций;
- появление трафика.

Для контроля фактической индексации всё равно нужны Яндекс Вебмастер, Google Search Console и Bing Webmaster Tools. Их подключение остаётся внешним действием владельца проекта.
