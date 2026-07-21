# Паркет36 — миграция кнопок на токены v1

## Цель

Перевести существующие production-кнопки на утверждённый контракт `Button`, не изменяя HTML, пользовательские сценарии, формы и интеграции.

Источник контракта:

- `design/components/parket36-components.json`;
- `design/parket36-tokens.json`.

## Область изменений

Миграция применяется к классу `.btn` и вариантам:

- `.btn--primary`;
- `.btn--ghost`;
- `.btn--light` — временная совместимость с существующей разметкой;
- `.btn--dark` — временная совместимость с существующей разметкой.

Основные production-варианты, соответствующие компонентному контракту:

- `primary`;
- `ghost`.

Вариант `secondary` остаётся в дизайн-контракте и будет внедрён, когда для него появится подтверждённый production-сценарий. Не следует массово менять существующие CTA только ради использования нового варианта.

## Размеры

Desktop:

- минимальная высота — 48 px;
- горизонтальные поля — 24 px;
- радиус — `radius.full`;
- минимальная зона взаимодействия не меньше 44 px.

Mobile до 640 px:

- минимальная высота сохраняется 52 px.

## Цвета

Primary:

- фон — `color.semantic.action.primary`;
- hover — `color.semantic.action.primaryHover`;
- текст — `color.semantic.text.inverse`.

Ghost:

- фон — `color.semantic.surface.default`;
- текст — `color.semantic.text.accent`;
- граница — `color.semantic.border.default`;
- hover-граница — `color.semantic.border.strong`.

Dark:

- фон — `color.semantic.bg.inverse`;
- текст — `color.semantic.text.inverse`.

Light:

- фон — `color.semantic.surface.default`;
- текст — `color.semantic.text.primary`;
- граница — `color.semantic.border.default`.

## Состояния

Обязательные состояния:

- default;
- hover;
- active;
- focus-visible;
- disabled.

Focus-state использует трёхпиксельный контур `color.primitive.brass.200` с отступом 3 px. Он видим не только за счёт изменения цвета фона.

Disabled-state использует одновременно:

- opacity 0.55;
- `cursor: not-allowed`;
- отсутствие transform;
- отсутствие тени.

## Порядок CSS

Токенизированный блок размещён в конце `css/cta-polish.css`.

Этот модуль собирается после `enhancements.css` и `accessibility-polish.css`, поэтому он явно отменяет старый древесный градиент через `background-image: none` и уточняет focus-state только для `.btn`.

## Что не меняется

- тексты и ссылки кнопок;
- телефон `+79009267929`;
- якоря `#request`;
- обработчики кликов;
- события аналитики;
- отправка заявок;
- Supabase endpoint;
- мобильная нижняя панель `.mobile-cta` — она будет мигрироваться отдельно.

## Проверка

```bash
python tools/check_button_token_migration.py
python tools/run_quality_checks.py
```

Дополнительно обязательны:

- Browser smoke;
- axe;
- Lighthouse CI;
- проверка reduced-motion;
- проверка mobile 390 px.
