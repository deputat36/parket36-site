# Следующие действия по проекту

Файл фиксирует только то, что нельзя полностью закрыть без ручной проверки, внешнего доступа или подтверждённых данных.

## Публикация сайта

Переключение `parket36.ru` на GitHub Pages завершено и подтверждено автоматической post-deploy проверкой.

Подтверждено:

- DNS направлен на GitHub Pages;
- HTTPS работает;
- публикуется Actions artifact `_site`, а не корень `main`;
- `/deployment.json` совпадает с SHA и run ID завершившегося Pages deploy;
- главная, `robots.txt` и `sitemap.xml` проходят live monitoring;
- issue #5 закрыто после фактического подтверждения публикации.

Документация: `docs/github-pages-switch-checklist.md`, `docs/live-site-monitoring.md`, `docs/deployment-manifest-cache.md`.

## Production Edge Function и заявки

Что осталось выполнить вручную:

1. Настроить в Supabase:
   - `PARKET_IP_HASH_SALT`;
   - `PARKET_HEALTHCHECK_TOKEN`;
   - параметры выбранного канала уведомлений.
2. Развернуть актуальную функцию `parket-public-lead`.
3. Добавить тот же `PARKET_HEALTHCHECK_TOKEN` в GitHub Actions secrets.
4. Запустить workflow `Production lead endpoint health`.
5. Убедиться, что функция и обе таблицы получают `PASS`.
6. Выполнить одну контролируемую реальную заявку.
7. Проверить строку в `parket_leads`, audit-запись и фактическое уведомление Ивану.

До появления GitHub secret workflow создаёт только безопасный отчёт `NOT CONFIGURED` и не отправляет запрос.

Порядок проверки: `docs/lead-endpoint-test-mode.md` и `docs/production-lead-monitoring.md`.

## Поисковые кабинеты и аналитика

Нужно вручную:

- добавить сайт в Яндекс Вебмастер и отправить sitemap;
- добавить сайт в Google Search Console и отправить sitemap;
- добавить сайт в Bing Webmaster Tools и проверить отчёт IndexNow;
- создать счётчик и заполнить `metrika_id` в `data/site.json`;
- проверить реальные цели звонка, оценки по фото и обратного звонка по `docs/analytics-events.md`.

Порядок действий: `docs/search-discovery-launch.md`.

## Issue #4 — подтверждённые материалы

Нужно получить от владельца проекта или Ивана:

- персональную ссылку в MAX;
- минимальный заказ и стоимость выезда;
- диапазоны цен по основным работам;
- подтверждённый стаж;
- реальные условия гарантии или формулировку без гарантии;
- фактический режим приёма звонков;
- 10–20 фотографий выполненных работ;
- 3–5 реальных отзывов с разрешением на публикацию;
- статус исполнителя: частный мастер, самозанятый или ИП.

После получения:

- заполнить `docs/confirmed-materials-template.md`;
- проверить материалы по `docs/photo-materials-checklist.md`;
- зафиксировать, что можно публиковать;
- обновить цены, страницу мастера, портфолио, отзывы и внешние карточки.

Индекс документов: `docs/materials-index.md`.

## Закрытые решения

- Issue #5 закрыто: production-домен публикует подтверждённую `_site`-сборку.
- Issue #283 закрыт: `tools/report_advice_index_gaps.py` остаётся ручным информационным отчётом и не блокирует общий quality gate.
