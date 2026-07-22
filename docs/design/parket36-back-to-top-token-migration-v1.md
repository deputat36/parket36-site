# Паркет36 — production-миграция Back to Top v1

## Scope

Компонент: глобальная кнопка `.back-to-top`, создаваемая в `js/main.js` на каждой публичной странице.

Production CSS: `css/back-to-top-polish.css`.

Контракт: `design/components/parket36-components.json` → `backToTop`.

Figma: компонент `Back to Top` остаётся `pending`, пока лимит Figma MCP Starter блокирует чтение и запись.

## Сохранённая логика

JavaScript не изменяется.

Кнопка:

- создаётся как нативный `<button>`;
- получает класс `.back-to-top`;
- содержит символ `↑`;
- имеет `aria-label="Вернуться к началу страницы"`;
- становится видимой через класс `.is-visible` после прокрутки более 650 px;
- прокручивает страницу к `top: 0`;
- использует `behavior: smooth`, если motion разрешён;
- использует `behavior: auto` при `prefers-reduced-motion: reduce`.

## Визуальные состояния

- `hidden` — opacity 0, pointer-events none, небольшое смещение вниз;
- `visible` — opacity 1, pointer-events auto;
- `hover` — более тёмный forest, brass border и подъём на 3 px;
- `focus` — отдельное brass focus-ring;
- `pressed` — уменьшение масштаба и card shadow.

## Размеры и положение

- размер — 48×48 px;
- минимальная зона взаимодействия — 44 px;
- радиус — `radius.full`;
- desktop: справа 18 px, снизу 22 px;
- mobile до 640 px: справа 18 px, снизу 82 px;
- мобильное положение сохраняет кнопку над фиксированной Mobile CTA.

## Токены

Используются только `--p36-*`:

- `color.semantic.action.primary`;
- `color.semantic.action.primaryHover`;
- `color.semantic.action.secondary`;
- `color.semantic.text.inverse`;
- `color.semantic.border.strong`;
- `color.primitive.brass.200`;
- `size.touchMin`;
- `radius.full`;
- `font.weight.extrabold`;
- `shadow.card`;
- `shadow.floating`.

Raw hex, rgb, rgba, hsl и hsla в новом CSS-блоке запрещены.

## Production bundle

`back-to-top-polish.css` расположен:

1. после `choice-chip-polish.css`;
2. перед `logo-brand.css`.

Публичная сборка продолжает содержать один cache-busted CSS-бандл.

## Не изменяется

- HTML публичных страниц;
- логика создания кнопки;
- порог 650 px;
- обработчик прокрутки;
- доступное имя;
- формы и payload;
- аналитика;
- Supabase и backend.

## Проверка

```bash
python tools/check_back_to_top_token_migration.py
python tools/run_quality_checks.py
```

Fail-closed validator проверяет контракт, каталог, CSS, JS-создание кнопки, порог, accessible name, reduced motion и порядок production bundle.
