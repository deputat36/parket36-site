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

## Production Edge Functions и заявки

Сначала выполнить единый безопасный аудит готовности:

1. Открыть `Actions → Production lead launch readiness`.
2. Выбрать ветку `main`.
3. Оставить политику `require-configured`, если Telegram или email должны работать сразу после deploy.
4. Запустить workflow.
5. Скачать artifact `production-lead-launch-readiness`.
6. Устранить все причины уровня `BLOCKED` или `DEPLOY_READY`.

Этот workflow:

- запускает Deno tests и type-check обеих функций;
- проверяет наличие GitHub deploy secrets;
- проверяет имена remote Supabase secrets;
- проверяет GitHub secrets controlled smoke;
- выполняет только публичный HTTP OPTIONS preflight;
- не использует environment `production`;
- не развёртывает функции;
- не вызывает protected healthcheck;
- не создаёт заявку.

Документация: `docs/production-lead-launch-readiness.md`.

Для полного запуска должны быть настроены:

### GitHub Actions secrets

- `SUPABASE_ACCESS_TOKEN`;
- `SUPABASE_PROJECT_ID` со значением project ref `ofewxuqfjhamgerwzull`;
- `PARKET_HEALTHCHECK_TOKEN`;
- `PARKET_SMOKE_CONTACT`.

### Supabase Edge Function secrets

- `PARKET_IP_HASH_SALT`;
- `PARKET_HEALTHCHECK_TOKEN`;
- полный Telegram-канал или полный email-канал.

После уровня `LAUNCH_READY` выполнить:

1. `Deploy production lead function` с `operation=validate-only`.
2. Проверить artifacts `edge-github-secret-readiness` и `edge-deploy-readiness`.
3. Отдельно запустить тот же workflow с `operation=deploy` и точной фразой `DEPLOY_PARKET_PUBLIC_LEAD`.
4. Подтвердить environment `production`.
5. Получить PASS public preflight и protected healthcheck.
6. Убедиться, что monitoring issue #375 закрылся автоматически.
7. Запустить `Controlled production lead smoke` с `operation=validate-only`.
8. Отдельно выполнить один `operation=send` с точной фразой `SEND_CONTROLLED_LEAD`.
9. Проверить строку в `parket_leads`, принятую audit-запись и фактическое уведомление Ивану.
10. Закрыть issue #373 только после подтверждения получения уведомления.

Порядок deploy: `docs/production-edge-deploy.md`.
Порядок controlled smoke: `docs/controlled-production-lead-smoke.md`.

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
