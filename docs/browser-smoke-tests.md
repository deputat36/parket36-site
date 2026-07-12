# Браузерные smoke-тесты Паркет36

Дата обновления: 2026-07-11.

Workflow: `.github/workflows/browser-smoke.yml`.

Конфигурация: `playwright.config.mjs`.

Основные тесты: `tests/e2e/site-smoke.spec.mjs`.

## Что проверяется

- главная страница, основной H1 и телефон Ивана;
- браузерное событие клика по телефону;
- открытие мобильного меню и закрытие по `Escape`;
- подстановка шаблона задачи в форму;
- успешная отправка заявки при корректном ответе backend;
- наличие пустых honeypot-полей в payload;
- live-region статуса формы: `role=status`, `aria-live=polite`, `aria-atomic=true`;
- `aria-invalid` и фокус на первом незаполненном обязательном поле;
- `aria-busy=true` во время отправки и возврат к `false` после ответа;
- блокировка повторного submit: при двойной отправке backend получает ровно один запрос;
- две попытки отправки при ответе backend `503`;
- появление ручного fallback-текста, если backend и clipboard недоступны;
- `noindex` и рабочие переходы на странице `404.html`;
- реальные размеры, lazy-loading, decoding и alt изображений портфолио;
- единый PNG в Open Graph, Twitter Card и JSON-LD.

## Изоляция от production

Тесты не создают реальные заявки и не обращаются к production-таблицам Supabase.

Playwright перехватывает запросы к `parket-public-lead` и возвращает контролируемые ответы:

- `200` для проверки успешного сценария;
- отложенный `200` для проверки busy-state и защиты от повторной отправки;
- `503` для проверки retry и fallback.

Отдельный тест развёрнутого production endpoint выполняется только после настройки обязательных Edge Function secrets.

## Локальный запуск

Требуются Node.js 20+, Python 3.12+ и Chromium Playwright.

```bash
npm install --no-audit --no-fund
npx playwright install chromium
npm run test:e2e
```

Playwright сам:

1. запускает `python tools/build_pages.py`;
2. поднимает локальный сервер на `127.0.0.1:4173`;
3. выполняет тесты против собранной папки `_site`;
4. останавливает сервер после завершения.

## GitHub Actions

Workflow запускается:

- для каждого Pull Request;
- после изменения ветки `main`;
- еженедельно;
- вручную через `workflow_dispatch`.

При ошибке сохраняются:

- HTML-отчёт `playwright-report`;
- trace;
- screenshot;
- video проблемного теста.

Artifact `browser-smoke-report` хранится 14 дней.

## Ограничения

Smoke-тесты проверяют критические пользовательские сценарии, но не заменяют:

- проверку реального production endpoint;
- accessibility-аудит axe;
- Lighthouse CI;
- ручную проверку на реальных мобильных устройствах.