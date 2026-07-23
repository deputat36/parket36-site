# Паркет36 — миграция Proof Card на дизайн-токены v1

## Назначение

Proof Card — неинтерактивный информационный блок с проверяемым фактом, условием, ограничением или правилом до начала работ. Компонент помогает укрепить доверие без выдуманных отзывов, цен и гарантий.

## Production-инвентарь

На момент миграции сайт содержит 27 элементов `.proof-card` на пяти публичных страницах:

- главная страница — 6;
- `/kak-rabotaem/` — 6;
- `/resheniya/` — 6;
- `/resheniya/dlya-rieltorov-i-sobstvennikov/` — 6;
- `/uslugi/melkiy-remont/` — 3.

Каждый элемент сохраняет структуру:

```html
<article class="proof-card">
  <strong>Заголовок</strong>
  <p>Описание</p>
</article>
```

## Контракт

Анатомия:

- Accent;
- Title;
- Description.

Размеры:

- минимальная высота — 156 px на широких экранах;
- внутреннее поле — 24 px;
- gap — 10–12 px;
- accent — 48×4 px;
- радиус — `radius.lg`.

## Неинтерактивность

Proof Card не является ссылкой, кнопкой или переключателем. Запрещены:

- `<a>` и `<button>` внутри карточки;
- `role="button"` или `role="link"`;
- `tabindex`;
- курсор `pointer`;
- hover-transform;
- focus, pressed и selected states.

Старое правило `.proof-card:hover { transform: translateY(-4px) }` нейтрализуется в новом слое через `transform: none`. Hover не меняет положение, границу или тень карточки.

## Визуальный слой

`css/proof-card-polish.css` использует только `--p36-*`:

- `surface.default`;
- `border.default`;
- `text.primary`, `text.secondary`, `text.accent`;
- `action.secondary` для brass-маркера;
- `radius.lg`;
- `shadow.card`;
- spacing и typography tokens.

Модуль расположен после `breadcrumbs-polish.css` и перед `logo-brand.css` в едином cache-busted production bundle.

## Мобильное поведение

До 640 px минимальная высота снимается, а внутреннее поле уменьшается до 16 px. Текст не обрезается и не получает фиксированное количество строк.

## Reduced motion

При `prefers-reduced-motion: reduce` компонент сохраняет `transition: none` и `transform: none`.

## Что не изменяется

- production HTML;
- заголовки и описания карточек;
- порядок карточек;
- сетки `.proof-grid`;
- ссылки соседних блоков;
- JavaScript;
- формы и payload;
- аналитика;
- Supabase и backend.

## Figma

До восстановления Figma MCP компонент хранится в `design/figma/parket36-sync-manifest.json` как:

```json
{"nodeId": null, "status": "pending"}
```

Фиктивный node ID запрещён.

## Проверка

```bash
python tools/check_proof_card_token_migration.py
python tools/run_quality_checks.py
```
