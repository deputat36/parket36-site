# Автоматический контроль parket36.ru

Workflow: `.github/workflows/live-site-health.yml`.

Основные скрипты:

- `tools/check_live_site.py` — DNS, HTTPS, главная, `www`, robots и sitemap;
- `tools/check_live_health_workflow.py` — статический контракт базовой live-проверки;
- `tools/check_live_conversion.py` — телефонный маршрут, собранная shared shell и публичный IndexNow-ключ;
- `tools/check_live_public_copy.py` — отсутствие редакторских заглушек на главной;
- `tools/check_live_deployment.py` — источник и точная версия Pages artifact;
- `tools/manage_live_health_issue.py` — единое issue при повторяющемся сбое;
- `tools/complete_pages_switch_issue.py` — завершение issue #5 после подтверждённого deploy.

## Что проверяется

### DNS и маршрутизация

Корневой домен `parket36.ru` должен разрешаться во все четыре рекомендуемые IPv4 GitHub Pages:

- `185.199.108.153`;
- `185.199.109.153`;
- `185.199.110.153`;
- `185.199.111.153`.

Ожидаемые IPv6 GitHub Pages допускаются дополнительно. Посторонние адреса считаются признаком старого хостинга, прокси или ошибочной DNS-записи.

`www.parket36.ru` должен разрешаться хотя бы в один официальный адрес GitHub Pages, а HTTPS-запрос должен завершаться на корневом `https://parket36.ru/`.

DNS проверяется один раз за запуск. Cache-busting к DNS неприменим.

### Базовый HTTP-контур

Одной попыткой проверяются:

- HTTPS и HTTP 200 главной;
- бренд, отображаемый телефон и действие `Оценка по фото`;
- отсутствие `WhatsApp` и `wa.me`;
- HTTPS-переход `www` на корневой домен;
- доступность `robots.txt`;
- строки `Sitemap` и `Host` в robots;
- доступность и XML-корректность `sitemap.xml`;
- минимальное количество sitemap URL и единый домен.

Каждый запрос получает уникальные параметры:

- `verify_live_health`;
- `check`;
- `attempt`.

Также отправляются заголовки:

- `Cache-Control: no-cache, no-store, max-age=0`;
- `Pragma: no-cache`.

Это не даёт нескольким попыткам повторно получить один устаревший CDN-объект. Query nonce не записывается в отчёт: сохраняются чистый публичный URL и `cache_bust_attempt`.

В post-deploy режиме выполняется до шести полных HTTP-попыток с интервалом 10 секунд. Ежедневный и ручной запуск выполняют одну попытку.

### Звонок, shared shell и IndexNow-ключ

Отдельная проверка требует одновременно:

- точную ссылку `href="tel:+79009267929"`, сформированную из `data/site.json`;
- отображаемый номер телефона;
- подпись `Позвонить Ивану`;
- действие `Оценка по фото`;
- четыре build-маркера shared shell;
- признак собранного CSS bundle;
- HTTP 200 публичного IndexNow-файла;
- точное совпадение файла с ключом из `data/indexnow.json`.

Этот контур также использует cache-busting и до шести попыток после deploy.

### Клиентский текст главной

`tools/check_live_public_copy.py` блокирует редакторские формулировки и требует клиентские инструкции по фотографиям пола. Проверка выполняется с уникальным query URL на каждой попытке.

### Источник и версия публикации

Workflow `Deploy GitHub Pages` создаёт `_site/deployment.json` перед загрузкой artifact.

Manifest содержит:

- `publisher: github-actions`;
- `artifact: _site`;
- SHA опубликованного коммита;
- ID запуска deploy workflow.

Post-deploy monitoring требует точного совпадения live SHA и run ID с завершившимся `Deploy GitHub Pages`. Плановый и ручной запуск проверяют manifest без требования конкретной версии.

## Когда запускается

Проверка запускается:

1. после каждого успешно завершённого `Deploy GitHub Pages`;
2. ежедневно по расписанию;
3. вручную через `workflow_dispatch`.

После deploy checkout выполняется по `workflow_run.head_sha`. Неуспешный Pages workflow не запускает live-health: красный deploy уже является отдельным сигналом ошибки.

## Диагностический отчёт

Каждый запуск создаёт artifact `live-health-report` с файлом `live-health-report.md`. Срок хранения — 30 дней.

Отчёт показывает:

- DNS-адреса и отклонения;
- чистые конечные HTTP URL;
- номер cache-busted попытки;
- общее количество использованных HTTP-попыток;
- состояние главной, `www`, robots и sitemap;
- телефонный маршрут и build-маркеры;
- клиентский текст главной;
- доступность IndexNow-ключа;
- опубликованный SHA и workflow run ID.

Если хотя бы одна проверка не прошла, artifact всё равно загружается, после чего workflow завершается ошибкой.

## Monitoring issue

Первый единичный сбой сохраняет красный workflow и artifact без создания задачи.

Если следующий завершённый запуск этого workflow также неуспешен, создаётся одно issue:

`[monitoring] parket36.ru live health failure`

Следующие сбои добавляют комментарии в открытую задачу. Первый успешный запуск после восстановления добавляет recovery-комментарий и закрывает issue.

Issue #5 и monitoring issue имеют разные роли: issue #5 подтверждает первоначальное переключение на Pages, monitoring issue отражает текущий повторный технический сбой.

## Права workflow

Используются минимальные разрешения:

- `contents: read`;
- `actions: read`;
- `issues: write`.

`permissions: write-all` запрещён CI-проверками. Ошибка GitHub API в служебном issue-шаге не подменяет результат фактической live-проверки.

## Ручные команды

Одна базовая проверка:

```bash
python tools/check_live_site.py \
  --report live-health-report.md \
  --attempts 1 \
  --timeout 20
```

Проверка с post-deploy retries:

```bash
python tools/check_live_site.py \
  --report live-health-report.md \
  --attempts 6 \
  --retry-delay 10 \
  --timeout 20
```

Проверка звонка и IndexNow-ключа:

```bash
python tools/check_live_conversion.py \
  --report live-health-report.md \
  --attempts 1 \
  --timeout 20
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

Офлайн-проверки:

```bash
python tools/check_live_site.py --self-test
python tools/check_live_health_workflow.py
python tools/check_live_conversion.py --self-test
python tools/check_live_conversion_workflow.py
python tools/check_live_public_copy_workflow.py
python tools/check_live_deployment.py --self-test
python tools/check_post_deploy_verification.py
python tools/complete_pages_switch_issue.py --self-test
python tools/manage_live_health_issue.py --self-test
```

Боевые issue-manager скрипты предназначены только для GitHub Actions, потому что требуют `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID` и контекст конкретного workflow.

## Ограничения

Проверка не меняет DNS, Pages settings, сертификат или содержимое сайта. Она фиксирует фактическое состояние публичного домена и опубликованной версии.

Успешная live-проверка не подтверждает production-готовность Supabase Edge Function, доставку заявок, поисковую индексацию или наличие трафика. Эти контуры проверяются отдельно.
