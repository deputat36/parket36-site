# Паркет36 — production-слой дизайн-токенов v1

## Назначение

Новая дизайн-система внедряется в действующий сайт небольшими проверяемыми PR. Сначала в production-бандл был добавлен самостоятельный слой токенов без изменения внешнего вида, затем началась последовательная миграция отдельных компонентов.

Такой подход не требует одновременно заменять всю вёрстку, формы, аналитику и интеграцию с Supabase.

## Источник истины

Исходные значения хранятся в:

- `design/parket36-tokens.json`.

Скрипт `tools/build_design_token_css.py` создаёт две байт-в-байт одинаковые копии:

- `design/generated/parket36-tokens.css` — для внутренних прототипов и Figma-синхронизации;
- `css/design-tokens.css` — для production CSS-бандла.

Редактировать сгенерированные CSS-файлы вручную запрещено.

## Production-подключение

`css/design-tokens.css` подключается первым модулем в `CSS_MODULES` файла `tools/css_bundle.py`.

Слой содержит 80 CSS-переменных с префиксом `--p36-`:

- примитивные и семантические цвета;
- интервалы;
- радиусы;
- базовые размеры;
- семейства, размеры и начертания шрифтов;
- тени.

## Разрешённые потребители

Первый визуальный потребитель токенов — `css/cta-polish.css`.

В нём на новую систему последовательно переведены:

- базовые кнопки `.btn` и их состояния;
- признаки доверия `.trust span`, соответствующие компоненту Badge;
- четыре ссылки `.quick-choice__grid a`, соответствующие компоненту Problem Card;
- поля `.request-form`, соответствующие компоненту Input, включая состояния default, focus, filled, error и disabled;
- фиксированная панель `.mobile-cta` с двумя действиями, safe-area и состояниями default/hover/focus/pressed.

Второй разрешённый потребитель — `css/typography-polish.css`.

В нём на токены переведены:

- общий компонент Section Header: `.section__head`, eyebrow, heading, description, разделитель и модификатор `.section__head--center`;
- нативный FAQ Item: `.faq details`, `.faq summary`, ответы, closed/open/hover/focus и индикатор `+`/`−`.

Третий разрешённый потребитель — `css/enhancements.css`.

В конце этого файла расположен отдельный блок `tokenized Service Card`. Он переводит карточки `.service-card` на варианты compact и media, сохраняя существующие ссылки, изображения и сетку.

Остальные production CSS-модули пока продолжают использовать прежние значения и не должны обращаться к `var(--p36-...)`.

Fail-closed guardrail разрешает следующий набор потребителей:

```text
css/cta-polish.css
css/enhancements.css
css/typography-polish.css
```

Новый потребитель нельзя добавлять скрытно. Для каждого следующего компонента нужно обновить список, отдельную спецификацию и автоматическую проверку.

## Границы выполненных миграций

Изменяются только визуальные свойства компонентов:

- цвет фона и текста;
- граница;
- радиус;
- интервалы;
- тень;
- состояния, когда они предусмотрены контрактом;
- декоративная нумерация Problem Card через CSS counter;
- максимальная ширина и выравнивание Section Header;
- текстовая подсказка ошибки Input для `:user-invalid`;
- compact и media оформление Service Card, включая подтверждённые изображения с `alt`;
- нативные closed/open/hover/focus состояния FAQ Item с индикатором `+`/`−`;
- Mobile CTA с двумя действиями, breakpoint 1000 px, safe-area и нижним отступом страницы.

Не изменяются:

- HTML и тексты страниц;
- уровни заголовков;
- ссылки и телефон;
- обработчики JavaScript;
- ID, required и metadata полей;
- формирование payload и fallback;
- FAQPage JSON-LD;
- аналитика;
- Supabase.

Следующий компонентный PR должен мигрировать только один новый тип интерфейса и пройти Browser smoke, axe и Lighthouse.

## Проверка

```bash
python tools/build_design_token_css.py --check
python tools/check_production_design_token_layer.py
python tools/check_button_token_migration.py
python tools/check_badge_token_migration.py
python tools/check_problem_card_token_migration.py
python tools/check_section_header_token_migration.py
python tools/check_input_token_migration.py
python tools/check_service_card_token_migration.py
python tools/check_faq_item_token_migration.py
python tools/check_mobile_cta_token_migration.py
python tools/build_pages.py
```

Проверка должна подтверждать:

- обе CSS-копии совпадают;
- объявлено ровно 80 переменных;
- `design-tokens.css` расположен первым модулем;
- токены используют только утверждённые CSS-файлы;
- Button, Badge, Problem Card, Service Card, FAQ Item, Section Header, Input и Mobile CTA соответствуют контракту компонентов;
- публичная сборка содержит один cache-busted CSS-бандл.
