# Автоматический контроль parket36.ru

Workflow: `.github/workflows/live-site-health.yml`.

Скрипты:

- `tools/check_live_site.py` — проверка DNS, GitHub Pages и публичного сайта с созданием отчёта;
- `tools/deployment_manifest.py` — создание маркера публикации внутри `_site`;
- `tools/check_live_deployment.py` — проверка, что домен отдаёт именно Actions artifact, а не `main / root`;
- `tools/manage_live_health_issue.py` — управление одним issue при повторяющемся сбое.

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

### Источник публикации

Workflow `Deploy GitHub Pages` после успешного quality gate создаёт файл `_site/deployment.json` и только затем загружает Pages artifact.

Manifest содержит:

- `publisher: github-actions`;
- `artifact: _site`;
- SHA опубликованного коммита;
- ID workflow run.

`tools/check_live_deployment.py` запрашивает `https://parket36.ru/deployment.json` и дописывает результат в общий `live-health-report.md`.

Это позволяет различать два внешне похожих случая:

1. правильная публикация Actions artifact — manifest существует и проходит проверку;
2. ошибочная публикация `main / root`, старого хостинга или другой сборки — manifest отсутствует либо содержит неправильные поля.

Файл намеренно не хранится в корне репозитория и появляется только внутри загружаемого `_site`. Поэтому он является маркером фактического источника публикации, а не просто наличия сайта.

### Публичный сайт

- доступность сайта по HTTPS с проверкой сертификата;
- HTTP-код главной страницы;
- наличие на главной маркеров новой версии: бренд, телефон и оценка по фото;
- отсутствие `WhatsApp` и `wa.me` на главной;
- доступность `robots.txt`;
- правильные строки Sitemap и Host в `robots.txt`;
- доступность и корректность XML в `sitemap.xml`;
- минимальное количество URL и единый домен в sitemap.

## Расписание

Проверка запускается ежедневно через GitHub Actions и может быть запущена вручную через `workflow_dispatch`.

## Диагностический отчёт

После каждого запуска создаётся artifact `live-health-report` с файлом `live-health-report.md`. Artifact хранится 30 дней.

Отчёт показывает отдельно:

- фактические адреса корневого домена;
- отсутствующие IPv4 GitHub Pages;
- посторонние DNS-адреса;
- результат разрешения `www`;
- конечный адрес HTTPS-перехода с `www`;
- состояние главной, robots и sitemap;
- наличие manifest GitHub Actions artifact;
- SHA и workflow run опубликованной сборки.

Если хотя бы одна проверка не прошла, отчёт всё равно загружается, после чего workflow завершается с ошибкой. Так диагностика не теряется даже при недоступном домене.

## Автоматическое issue при повторном сбое

Механизм не создаёт issue после первого единичного сбоя.

Порядок:

1. Первый неуспешный запуск сохраняет artifact и завершается с ошибкой.
2. Если следующий завершённый запуск этого же workflow тоже был неуспешным, создаётся одно issue с заголовком `[monitoring] parket36.ru live health failure`.
3. Следующие неуспешные запуски добавляют комментарий в уже открытое issue вместо создания новых задач.
4. Первый успешный запуск после восстановления добавляет комментарий и закрывает issue.

В issue попадают ссылка на workflow run и содержимое диагностического отчёта. Secrets и персональные данные туда не передаются.

## Права workflow

Workflow использует минимально необходимые разрешения:

- `contents: read` — чтение репозитория;
- `actions: read` — проверка результата предыдущего workflow run;
- `issues: write` — создание, обновление и закрытие monitoring issue.

`permissions: write-all` запрещён проверкой конфигурации.

Ошибки GitHub API при управлении issue не подменяют результат проверки сайта: шаг issue-manager имеет `continue-on-error`, а итоговый workflow всё равно завершается согласно результатам основной health-проверки и проверки источника публикации.

## Ручной запуск скриптов

Проверка сайта:

```bash
python tools/check_live_site.py --report live-health-report.md
```

Проверка источника публикации с добавлением результата в тот же отчёт:

```bash
python tools/check_live_deployment.py --report live-health-report.md
```

Офлайн self-test DNS-оценки и отчёта:

```bash
python tools/check_live_site.py --self-test
```

Офлайн self-test manifest и проверки источника:

```bash
python tools/deployment_manifest.py --self-test
python tools/check_live_deployment.py --self-test
```

Офлайн self-test issue-manager:

```bash
python tools/manage_live_health_issue.py --self-test
```

Боевой запуск issue-manager предназначен только для GitHub Actions, потому что требует `GITHUB_TOKEN`, `GITHUB_REPOSITORY` и `GITHUB_RUN_ID`.

## Ограничения

Проверка не меняет DNS, Pages settings или сертификат. Она фиксирует фактическое состояние публичного сайта и источник отданной сборки. Настройка DNS, Custom domain и Enforce HTTPS остаётся ручным действием по issue #5.

Issue создаётся только после двух последовательных неуспешных запусков. Если GitHub API временно недоступен, artifact и красный статус workflow сохраняются, но issue может быть создан только при следующем сбое.
