# Паркет36 — production-миграция Mobile CTA v1

## Цель

Перевести фиксированную мобильную панель быстрых действий на дизайн-токены без изменения HTML, ссылок, JavaScript, форм и backend.

## Production scope

- компонент: `.mobile-cta`;
- действия: `.mobile-cta a`;
- CSS: `css/cta-polish.css`;
- breakpoint: `max-width: 1000px`.

## Контракт

Панель содержит ровно два действия в фиксированном порядке:

1. звонок по `tel:+79009267929`;
2. переход к оценке по фото или заявке.

Размеры:

- максимальная ширина — 620 px;
- минимальная высота действия — 52 px;
- gap — 8 px;
- padding контейнера — 8 px;
- радиус контейнера — `radius.lg`;
- радиус действий — `radius.md`.

## Состояния

- `default` — forest primary и brass secondary;
- `hover` — соответствующие hover-токены;
- `focus` — отдельный `:focus-visible`;
- `pressed` — уменьшение масштаба без изменения назначения действия.

## Доступность

- минимальная зона взаимодействия — 44 px;
- фактическая высота действия — 52 px;
- focus-state видим независимо от цвета;
- панель учитывает `env(safe-area-inset-bottom)`;
- `body` получает достаточный нижний отступ;
- `prefers-reduced-motion` отключает transition и transform.

## Сохранённые данные

Не изменяются:

- тексты ссылок на публичных страницах;
- телефон `+79009267929`;
- порядок двух действий;
- переходы к форме или странице заявки;
- HTML;
- `js/main.js`;
- формы, аналитика, payload и Supabase.

## Figma

Целевой компонент: `Mobile CTA` на странице `Foundations + Components — Дизайн-система`.

Из-за лимита Figma MCP Starter компонент записан в sync manifest как:

- `nodeId: null`;
- `status: pending`.

Это спецификация будущего компонента, а не подтверждение созданного Figma-узла.

## Проверка

```bash
python tools/check_design_component_catalog.py
python tools/check_design_foundations.py
python tools/check_mobile_cta_token_migration.py
python tools/run_quality_checks.py
```

После статических проверок обязательны Site quality, Lighthouse CI и Browser smoke на одном SHA.
