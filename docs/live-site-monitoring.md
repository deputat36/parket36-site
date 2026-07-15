# Автоматический контроль parket36.ru

Workflow: `.github/workflows/live-site-health.yml`.

Скрипты:

- `tools/check_live_site.py` — проверка DNS, GitHub Pages и публичного сайта с созданием отчёта;
- `tools/check_live_conversion.py` — проверка рабочего `tel:`-маршрута, подписей звонка и публичного IndexNow-ключа;
- `tools/check_live_deployment.py` — проверка источника и точной версии опубликованного Pages artifact;
- `tools/deployment_manifest.py` — создание `_site/deployment.json` внутри Pages workflow;
- `tools/manage_live_health_issue.py` — управление одним issue при повторяющемся сбое;
- `tools/complete_pages_switch_issue.py` — закрытие issue #5 после подтверждённого post-deploy успеха.

## Что проверяется

### DNS и GitHub Pages

- корневой домен `parket36.ru` должен разрешаться во все четыре рекомендуемые IPv4 GitHub Pages:
  - `185.199.108.153`;
  - `185.199.109.153`;
  - `185.199.110.153`;
  - `185.199.111.153`;
- ожидаемые IPv6 GitHub Pages допускаются дополнительно;
- посторонние адреса считаются признаком старого хостинга, прокси или ошибочной записи;
- `www.parket36.ru` должен разрешаться хотя бы в один официальный адрес GitHub Pages и не содержать посторонних адресов;
- HTTPS-запрос к `www.parket36.ru` должен завершаться на корневом `https://parket36.ru/`.

Проверка `www` подтверждает фактическую маршрутизацию на инфраструктуру GitHub Pages. Она не извлекает саму CNAME-запись, поэтому правильное значение `www → deputat36.github.io` дополнительно проверяется в панели DNS при настройке issue #5.

### Публичный сайт

- доступность сайта по HTTPS с проверкой сертификата;
- HTTP-код главной страницы;
- наличие на главной маркеров новой версии: бренд, телефон и оценка по фото;
- отсутствие `WhatsApp` и `wa.me` на главной;
- доступность `robots.txt`;
- правильные строки Sitemap и Host в `robots.txt`;
- доступность и корректность XML в `sitemap.xml`;
- минимальное количество URL и единый домен в sitemap.

### Звонок и IndexNow

Отдельный live-check повторно читает боевую главную и требует одновременно:

- точную ссылку `href="tel:+79009267929"`, сформированную из `data/site.json`;
- отображаемый номер телефона из общих настроек;
- понятную подпись `Позвонить Ивану`;
- действие `Оценка по фото`.

Это защищает от ситуации, когда номер остаётся видимым текстом, но кликабельный телефонный маршрут исчезает из опубликованного HTML.

Также проверяется:

- HTTP 200 для `https://parket36.ru/indexnow-key.txt`;
- точное совпадение содержимого файла с ключом из `data/indexnow.json`.

В post-deploy режиме выполняется до шести попыток с интервалом 10 секунд, чтобы краткая задержка CDN не создавала ложный сбой. Ежедневный и ручной запуск выполняют одну попытку.

### Источник и версия публикации

Workflow `Deploy GitHub Pages` после успешного quality gate создаёт `_site/deployment.json` непосредственно перед загрузкой Pages artifact.

Manifest содержит:

- `publisher: github-actions`;
- `artifact: _site`;
- SHA опубликованного коммита;
- ID запуска workflow публикации.

Файл не хранится в корне репозитория. Поэтому:

- HTTP 200 и правильные поля подтверждают публикацию Actions artifact `_site`;
- HTTP 404 означает публикацию из `main / root`, старый хостинг или незавершённый deploy;
- неправильный publisher или artifact означает неверный источник;
- несовпадающий SHA или run ID означает, что домен ещё отдаёт предыдущую сборку.

После события `workflow_run` monitoring получает SHA и ID завершившегося `Deploy GitHub Pages` и требует точного совпадения с live manifest. Проверка выполняет до шести попыток с интервалом 10 секунд, чтобы краткая задержка GitHub Pages CDN не создавала ложный сбой.

## Когда запускается

Проверка запускается:

1. сразу после каждого успешно завершённого workflow `Deploy GitHub Pages`;
2. ежедневно по расписанию;
3. вручную через `workflow_dispatch`.

После deploy workflow checkout выполняется на `head_sha` опубликованной сборки. Проверка после неуспешного Pages workflow не запускается: красный deploy уже является отдельным сигналом ошибки.

Ежедневный и ручной запуск проверяют корректность manifest без требования конкретного SHA. Post-deploy запуск дополнительно требует точного SHA и run ID.

## Автоматическое завершение issue #5

Issue `#5 Переключить parket36.ru на GitHub Pages` закрывается автоматически только когда одновременно выполнены все условия:

1. workflow запущен событием `workflow_run` после успешного `Deploy GitHub Pages`;
2. DNS, HTTPS, главная, телефонный маршрут, IndexNow-ключ, `robots.txt` и `sitemap.xml` прошли live-проверку;
3. `/deployment.json` подтверждает Actions artifact `_site`;
4. live `commit` совпадает с `workflow_run.head_sha`;
5. live `run_id` совпадает с ID завершившегося Pages deploy.

Плановый и ручной monitoring не закрывают issue #5, даже если сайт работает. Это защищает задачу от завершения без привязки к конкретному опубликованному deploy.

Перед закрытием скрипт проверяет номер и точный заголовок issue. Затем добавляет комментарий с опубликованным SHA, ссылкой на Pages deploy и ссылкой на live verification и закрывает задачу со статусом `completed`.

Если issue уже закрыт, шаг завершается без изменений. Ошибка GitHub API не делает сам live-health запуск красным: автозавершение является служебным действием с `continue-on-error`, а доказательством публикации остаётся artifact-отчёт.

## Диагностический отчёт

После каждого запуска создаётся artifact `live-health-report` с файлом `live-health-report.md`. Artifact хранится 30 дней.

Отчёт показывает отдельно:

- фактические адреса корневого домена;
- отсутствующие IPv4 GitHub Pages;
- посторонние DNS-адреса;
- результат разрешения `www`;
- конечный адрес HTTPS-перехода с `www`;
- состояние главной, robots и sitemap;
- наличие точного `tel:`-маршрута и подписей звонка;
- доступность и точность IndexNow-ключа;
- наличие `/deployment.json`;
- publisher и artifact;
- опубликованный SHA и workflow run ID;
- ожидаемый SHA/run ID post-deploy проверки;
- количество попыток при задержке распространения.

Если хотя бы одна проверка не прошла, отчёт всё равно загружается, после чего workflow завершается с ошибкой. Так диагностика не теряется даже при недоступном домене.

## Автоматическое issue при повторном сбое

Механизм не создаёт issue после первого единичного сбоя.

Порядок:

1. Первый неуспешный запуск сохраняет artifact и завершается с ошибкой.
2. Если следующий завершённый запуск этого же workflow тоже был неуспешным, создаётся одно issue с заголовком `[monitoring] parket36.ru live health failure`.
3. Следующие неуспешные запуски добавляют комментарий в уже открытое issue вместо создания новых задач.
4. Первый успешный запуск после восстановления добавляет комментарий и закрывает monitoring issue.

Monitoring issue и issue #5 имеют разные роли: первое отражает повторный технический сбой, второе — одноразовую задачу переключения домена на правильную публикацию.

В issue попадают ссылка на workflow run и содержимое диагностического отчёта. Secrets и персональные данные туда не передаются. Значение IndexNow-ключа в отчёт не выводится.

## Права workflow

Workflow использует минимально необходимые разрешения:

- `contents: read` — чтение репозитория и checkout точного опубликованного SHA;
- `actions: read` — проверка результата предыдущего workflow run;
- `issues: write` — создание, обновление и закрытие monitoring issue и issue #5.

`permissions: write-all` запрещён проверкой конфигурации.

Ошибки GitHub API при управлении issue не подменяют результат проверки сайта: issue-шаги имеют `continue-on-error`, а итоговый workflow всё равно завершается согласно результату live health check.

## Ручной запуск скриптов

Проверка сайта:

```bash
python tools/check_live_site.py --report live-health-report.md
```

Проверка живого звонка и IndexNow-ключа:

```bash
python tools/check_live_conversion.py \
  --report live-health-report.md \
  --attempts 1 \
  --timeout 20
```

Проверка опубликованного Actions artifact без требования версии:

```bash
python tools/check_live_deployment.py --report live-health-report.md
```

Проверка конкретного deploy:

```bash
python tools/check_live_deployment.py \
  --report live-health-report.md \
  --expected-sha COMMIT_SHA \
  --expected-run-id WORKFLOW_RUN_ID \
  --attempts 6 \
  --retry-delay 10
```

Офлайн self-tests:

```bash
python tools/deployment_manifest.py --self-test
python tools/check_live_deployment.py --self-test
python tools/check_post_deploy_verification.py
python tools/complete_pages_switch_issue.py --self-test
python tools/check_live_site.py --self-test
python tools/check_live_conversion.py --self-test
python tools/check_live_conversion_workflow.py
python tools/manage_live_health_issue.py --self-test
```

Боевые issue-manager скрипты предназначены только для GitHub Actions, потому что требуют `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID` и контекст конкретного workflow.

## Ограничения

Проверка не меняет DNS, Pages settings или сертификат. Она фиксирует фактическое состояние публичного сайта, телефонного маршрута, IndexNow-ключа и точную опубликованную версию. Настройка DNS, Custom domain и Enforce HTTPS остаётся ручным действием до первого успешного post-deploy подтверждения.

Issue создаётся только после двух последовательных неуспешных запусков. Если GitHub API временно недоступен, artifact и красный статус workflow сохраняются, но issue может быть создан или закрыт только при следующем подходящем запуске.
