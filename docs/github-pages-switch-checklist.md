# Чек-лист переключения parket36.ru на GitHub Pages

Связанная задача: issue #5.

## Что уже есть в репозитории

- `CNAME` содержит `parket36.ru`.
- `robots.txt` указывает sitemap и host для `parket36.ru`.
- `.github/workflows/pages.yml` собирает сайт и публикует `_site` через GitHub Pages.
- `.github/workflows/site-quality.yml` запускает общий quality gate.
- `tools/check_guardrails.py` блокирует возврат `WhatsApp` и `wa.me` в публичные текстовые файлы.

## Что проверить вручную

1. Открыть настройки репозитория.
2. В разделе Pages выбрать источник GitHub Actions.
3. В Custom domain указать `parket36.ru`.
4. Проверить DNS у регистратора домена.
5. Дождаться проверки домена в GitHub Pages.
6. Включить Enforce HTTPS.
7. Запустить Deploy GitHub Pages вручную или дождаться запуска после push в `main`.
8. Проверить, что `https://parket36.ru/` открывает новую версию сайта.

## Результат ручной проверки

- [ ] Source выбран как GitHub Actions.
- [ ] Custom domain сохранён как `parket36.ru`.
- [ ] DNS у регистратора направлен на GitHub Pages.
- [ ] GitHub подтвердил домен.
- [ ] Enforce HTTPS включён.
- [ ] Deploy GitHub Pages завершился успешно.
- [ ] Новая версия сайта открывается по `https://parket36.ru/`.

## После переключения

- Проверить главную страницу.
- Проверить `/zayavka/`.
- Проверить `/kontakty/`.
- Проверить `/sitemap.xml`.
- Проверить клики по телефону на мобильном.
