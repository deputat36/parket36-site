# Чек-лист переключения parket36.ru на GitHub Pages

Связанная задача: issue #5.

## Что уже есть в репозитории

- `CNAME` содержит `parket36.ru`.
- `robots.txt` указывает sitemap и host для `parket36.ru`.
- `.github/workflows/pages.yml` собирает сайт и публикует `_site` через GitHub Pages.
- `.github/workflows/site-quality.yml` запускает общий quality gate.

## Что проверить вручную

1. Открыть настройки репозитория.
2. В разделе Pages выбрать источник GitHub Actions.
3. В Custom domain указать `parket36.ru`.
4. Проверить DNS у регистратора домена.
5. Дождаться проверки домена в GitHub Pages.
6. Включить Enforce HTTPS.
7. Запустить Deploy GitHub Pages вручную или дождаться запуска после push в `main`.
8. Проверить, что `https://parket36.ru/` открывает новую версию сайта.

## После переключения

- Проверить главную страницу.
- Проверить `/zayavka/`.
- Проверить `/kontakty/`.
- Проверить `/sitemap.xml`.
- Проверить клики по телефону на мобильном.
