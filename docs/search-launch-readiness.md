# Единая готовность поискового запуска

Workflow `.github/workflows/search-launch-readiness.yml` собирает один безопасный отчёт о технической готовности `parket36.ru` к подключению поисковых кабинетов и аналитики.

Он не меняет сайт, DNS, поисковые кабинеты или IndexNow. Проверка выполняет только чтение публичных файлов и конфигурации репозитория.

## Что проверяется

1. DNS корневого домена и `www` ведут на GitHub Pages.
2. Главная страница открывается по HTTPS и содержит основные маркеры.
3. `robots.txt` доступен и указывает правильный sitemap.
4. `sitemap.xml` валиден, содержит достаточное число URL и использует только `parket36.ru`.
5. Публичный файл ключа IndexNow доступен и совпадает с `data/indexnow.json`.
6. В `data/site.json` заполнен или не заполнен `metrika_id`.

## Как запустить

1. Открыть `Actions → Search launch readiness`.
2. Нажать `Run workflow`.
3. Выбрать ветку `main`.
4. Скачать artifact `search-launch-readiness` или открыть job summary.

Workflow запускается только вручную и только для default branch. Ему не нужны secrets, environment approval или доступы к поисковым кабинетам.

## Уровни готовности

### BLOCKED

Не прошла одна из технических проверок публичного домена, robots/sitemap или живого ключа IndexNow. Сначала нужно устранить конкретный FAIL из component report.

### TECHNICAL_READY_ANALYTICS_PENDING

Домен, robots, sitemap и IndexNow технически готовы, но `metrika_id` ещё не заполнен. Сайт можно добавлять в поисковые кабинеты, а аналитику нужно подключить отдельно.

### SEARCH_LAUNCH_READY

Технические проверки прошли и ID Яндекс Метрики присутствует в общей конфигурации. Этот уровень всё равно не доказывает, что права в кабинетах подтверждены или страницы уже попали в индекс.

## Состав artifact

- `search-launch-readiness.md` — единый итог и оставшиеся ручные действия;
- `search-live-health.md` — DNS, HTTPS, главная, robots и sitemap;
- `search-indexnow.md` — проверка живого ключа IndexNow.

## Что остаётся вручную

Даже при `SEARCH_LAUNCH_READY` необходимо:

- добавить сайт и sitemap в Яндекс Вебмастер;
- добавить сайт и sitemap в Google Search Console;
- добавить сайт и sitemap в Bing Webmaster Tools;
- проверить цели звонка и заявки после подключения Метрики;
- оценивать индексирование и позиции по данным самих кабинетов, а не по факту успешного workflow.

## Защита от лишних действий

Workflow:

- не вызывает `--submit` для IndexNow;
- не использует токены поисковых кабинетов;
- не пишет в issues;
- не меняет `data/site.json`;
- не публикует сайт;
- не выполняет production-заявки;
- не считает успешную техническую проверку гарантией индексации или позиций.

Локальная проверка контракта:

```bash
python tools/build_search_launch_readiness.py --self-test
python tools/check_search_launch_readiness.py
```
