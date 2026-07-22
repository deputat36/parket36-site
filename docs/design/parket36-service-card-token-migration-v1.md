# Паркет36 — миграция Service Card на токены

## Область изменения

Миграция распространяется только на существующие элементы `.service-card` и ссылки внутри них.

Поддерживаются два варианта:

- `compact` — номер или иконка, заголовок и описание;
- `media` — подтверждённое изображение реальной работы, заголовок и описание.

HTML, тексты, `href`, JavaScript, формы, аналитика и Supabase не изменяются.

## Контракт

Источник: `design/components/parket36-components.json`.

Service Card содержит:

- необязательный Media;
- необязательный Icon;
- Body;
- Title;
- Description.

Состояния: `default`, `hover`, `focus`.

Минимальная высота — 192 px. Внутренние поля — 24 px. Радиус — `radius.lg`. Соотношение изображения — `1000/760`.

Вся карточка остаётся ссылкой. Focus-state должен быть заметным независимо от hover. Изображение внутри карточки обязано иметь осмысленный `alt`.

## Production CSS

Tokenized-блок находится в конце `css/enhancements.css` после маркера:

```css
/* Design system v1: tokenized Service Card. */
```

В блоке запрещены raw hex/rgb цвета и старые переменные `--wood`, `--gold`, `--line`, `--radius`, `--shadow`.

Используются только `--p36-*` для:

- surface и текста;
- границы;
- радиуса;
- внутренних интервалов;
- card/floating shadow;
- focus-ring;
- оформления номера или иконки.

## Изображения

Медиа-вариант не разрешает подставлять выдуманные фотографии. Используются только подтверждённые изображения реальных работ. До появления такого изображения остаётся текстовый вариант или нейтральный placeholder во внутреннем каталоге.

## Адаптивность и движение

Существующая сетка `.services-grid` сохраняется:

- три колонки на широком экране;
- две колонки до 1000 px;
- одна колонка до 640 px.

При `prefers-reduced-motion: reduce` карточка не должна смещаться при hover.

## Проверка

```bash
python tools/check_design_component_catalog.py
python tools/check_service_card_token_migration.py
python tools/build_pages.py
```

Дополнительно обязательны Site quality, Lighthouse CI и Browser smoke.
