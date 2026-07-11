# Автоматизация sitemap Паркет36

## Цель

`tools/build_sitemap.py` формирует sitemap из фактических индексируемых HTML-страниц, а не из вручную набранного списка URL.

Источники:

- canonical каждой страницы;
- `meta robots` для исключения `noindex`;
- JSON-LD `dateModified`, затем `datePublished`;
- подтверждённые `lastmod`, `changefreq` и `priority` текущего sitemap как совместимый переходный слой.

## Проверка

Команда:

```bash
python tools/check_generated_sitemap.py
```

входит в общий quality gate и блокирует PR, если:

- индексируемая canonical-страница отсутствует;
- в sitemap остался удалённый или переведённый в `noindex` адрес;
- `dateModified` или `datePublished` расходится с `lastmod`;
- новый URL не имеет структурированной даты и ещё не имеет подтверждённого `lastmod`;
- присутствует конфликт индексируемых canonical.

## Генерация

```bash
python tools/build_sitemap.py \
  --source sitemap.xml \
  --output reports/generated-sitemap.xml
```

После проверки diff файл `reports/generated-sitemap.xml` заменяет корневой `sitemap.xml`.

Workflow `Site quality` всегда сохраняет candidate как artifact `generated-sitemap`, даже когда основной quality gate завершился ошибкой.

## Новая страница

Для новой индексируемой страницы:

1. указать canonical на `parket36.ru`;
2. использовать `index, follow`;
3. добавить в JSON-LD `datePublished` и `dateModified` в формате `YYYY-MM-DD`;
4. запустить генератор;
5. проверить diff и общий quality gate.

Для новых страниц применяются безопасные значения по умолчанию:

- главная — `weekly`, priority `1.0`;
- индекс раздела советов — `monthly`, `0.8`;
- статья совета — `yearly`, `0.72`;
- раздел услуг — `monthly`, `0.9`;
- вложенная услуга — `monthly`, `0.8`;
- раздел решений — `monthly`, `0.85`;
- вложенное решение — `monthly`, `0.8`;
- остальные страницы — `monthly`, `0.8`.

Существующие значения сохраняются, поэтому внедрение генератора не меняет приоритеты уже опубликованных страниц.

## Старый helper

`tools/add_sitemap_entry.py` и его self-test пока сохранены для обратной совместимости. Для новых материалов предпочтителен полный генератор, потому что он одновременно контролирует canonical, индексируемость и даты.
