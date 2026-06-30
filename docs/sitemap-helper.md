# Sitemap helper

`tools/add_sitemap_entry.py` добавляет одну страницу в `sitemap.xml` и защищает от дублей.

## Когда использовать

Используйте helper после добавления новой статической страницы, если страница должна индексироваться поисковиками.

## Пример

```bash
python tools/add_sitemap_entry.py /sovety/novaya-statya/ --lastmod 2026-06-30
```

Можно передать полный адрес сайта:

```bash
python tools/add_sitemap_entry.py https://parket36.ru/sovety/novaya-statya/ --lastmod 2026-06-30
```

## Параметры

- `path` — путь страницы или полный URL `https://parket36.ru/...`.
- `--lastmod` — дата в формате `YYYY-MM-DD`. По умолчанию используется текущая дата.
- `--changefreq` — частота изменения. По умолчанию `yearly`.
- `--priority` — приоритет. По умолчанию `0.72`.
- `--file` — путь к sitemap. По умолчанию `sitemap.xml`.

## Поведение

- если URL уже есть в sitemap, helper ничего не дублирует;
- если путь передан без слеша, helper добавит начальный и конечный `/`;
- если дата указана не в формате `YYYY-MM-DD`, helper завершится с ошибкой;
- если в файле нет `</urlset>`, helper завершится с ошибкой, чтобы не испортить XML.
