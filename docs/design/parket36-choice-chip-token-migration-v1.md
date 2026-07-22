# Паркет36 — production-миграция Choice Chip v1

## Цель

Перевести кнопки быстрого старта формы на дизайн-токены без изменения шаблонов, услуг, JavaScript, payload, аналитики и Supabase.

## Production scope

- контейнер: `.request-form .pill-row`;
- действия: `.request-form .pill-row .pill`;
- CSS: `css/choice-chip-polish.css`;
- страница: `index.html`;
- количество действий: 8.

## Семантика

Choice Chip — это action-chip, а не одиночный выбор или фильтр.

Каждая кнопка:

- использует нативный `<button type="button">`;
- содержит `data-request-template`;
- содержит `data-request-service`;
- добавляет шаблон в поле задачи через существующий обработчик;
- может применяться последовательно с другими шаблонами.

Поэтому постоянные `selected`, `aria-selected` и `aria-pressed` не добавляются. Состояние pressed существует только во время нажатия.

## Контракт

- вариант: `action`;
- состояния: `default`, `hover`, `focus`, `pressed`;
- минимальная высота — 44 px;
- горизонтальные поля — 16 px;
- gap контейнера — 8 px;
- радиус — `radius.full`;
- focus-state не зависит только от цвета;
- `prefers-reduced-motion` отключает transition и transform.

## Сохранённые данные

Не изменяются:

- восемь подписей кнопок;
- восемь значений `data-request-template`;
- восемь значений `data-request-service`;
- порядок кнопок;
- обработчик `[data-request-template]` в `js/main.js`;
- выбор option в `#request-service`;
- добавление текста в `#request-task`;
- событие `request-template`;
- форма, payload, fallback, аналитика и Supabase.

## Подключение

`choice-chip-polish.css`:

- подключён отдельной строкой в исходном `index.html` для локального просмотра;
- включён в `CSS_MODULES` после `cta-polish.css`;
- попадает в единый cache-busted production bundle;
- использует более специфичный селектор, чем старый fallback из `interface-polish.css`.

## Figma

Целевой компонент: `Choice Chip` на странице `Foundations + Components — Дизайн-система`.

Из-за лимита Figma MCP Starter компонент записан в sync manifest как:

- `nodeId: null`;
- `status: pending`.

Это спецификация будущего компонента, а не подтверждение созданного Figma-узла.

## Проверка

```bash
python tools/check_design_component_catalog.py
python tools/check_design_foundations.py
python tools/check_production_design_token_layer.py
python tools/check_choice_chip_token_migration.py
python tools/run_quality_checks.py
```

После статических проверок обязательны Site quality, Lighthouse CI и Browser smoke на одном SHA.
