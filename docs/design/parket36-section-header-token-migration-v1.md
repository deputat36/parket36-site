# Паркет36 — миграция Section Header на токены v1

## Область

На компонент Section Header переведены существующие контейнеры `.section__head` на публичных страницах сайта.

Компонент объединяет:

- Eyebrow — короткую надпись над заголовком;
- Heading — заголовок раздела;
- Description — поясняющий абзац;
- необязательную текстовую ссылку;
- декоративный разделитель после содержимого.

HTML, тексты и уровни заголовков не изменяются.

## Соответствие контракту

Контракт хранится в `design/components/parket36-components.json`.

Поддерживаются два выравнивания:

- `left` — стандартный `.section__head`;
- `center` — модификатор `.section__head--center` для будущих секций.

Максимальная ширина текста — 760 px. Расстояние между элементами — 16 px.

## Токены

- gap — `spacing.lg`, 16 px;
- нижний отступ — `spacing.2xl`, 32 px;
- eyebrow — `text.warm`, `font.size.eyebrow`, `font.weight.bold`;
- heading — `text.primary`;
- description — `text.secondary` с размером от 16 до 20 px;
- разделитель — `action.primary` → `action.secondary`;
- ширина разделителя — `spacing.4xl`, 64 px;
- высота разделителя — `spacing.xs`, 4 px.

## Мобильное поведение

До 640 px сохраняется существующий нижний отступ 22 px. Контейнер ограничен шириной `min(100%, 760px)`, поэтому горизонтального переполнения нет.

## Доступность и SEO

- уровни `h2` и другие заголовки не меняются;
- текст не заменяется изображением или псевдоэлементом;
- цвет описания сохраняет читаемый контраст;
- center-модификатор меняет только визуальное выравнивание;
- декоративный разделитель не несёт смысловой информации;
- focus-состояния текстовых ссылок продолжают обрабатываться общим accessibility-слоем.

## Не изменяется

- HTML и контент страниц;
- структура `h1`, `h2`, `h3`;
- ссылки и телефон;
- кнопки, Badge и Problem Card;
- JavaScript;
- формы и payload;
- аналитика;
- Supabase.

## Проверка

```bash
python tools/check_section_header_token_migration.py
python tools/check_production_design_token_layer.py
python tools/run_quality_checks.py
```

После изменения обязательны Site quality, Lighthouse CI и Browser smoke на desktop и mobile 390 px.
