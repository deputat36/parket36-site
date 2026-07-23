# Паркет36 — миграция Process Step на дизайн-токены v1

## Назначение

Process Step — неинтерактивный этап упорядоченного процесса: подготовки фотографий, диагностики, согласования, выполнения работ или ухода за покрытием.

Компонент помогает показать последовательность действий без превращения каждого шага в кнопку или ссылку.

## Production-инвентарь

На момент миграции `.steps` используется на 86 публичных страницах сайта. Всего найдено 87 ordered lists: на странице `/kontakty/` расположены два независимых процесса, на остальных страницах — по одному.

Каждый блок сохраняет нативную структуру:

```html
<ol class="steps">
  <li>
    <strong>Заголовок этапа</strong>
    <span>Описание этапа</span>
  </li>
</ol>
```

Номер этапа создаётся CSS-counter и не дублируется вручную в HTML.

## Контракт

Анатомия:

- Number;
- Title;
- Description.

Размеры:

- сетка — 3 колонки на широких экранах;
- gap — 16 px;
- минимальная высота карточки — 164 px;
- верхнее поле — 64 px;
- горизонтальные и нижнее поля — 24 px;
- номер — 36×36 px;
- радиус — `radius.lg`.

До 640 px сетка становится одноколоночной, минимальная высота снимается, а горизонтальные поля уменьшаются до 16 px.

## Семантика и неинтерактивность

Process Step обязан сохранять:

- `<ol class="steps">`;
- дочерние `<li>` в исходном порядке;
- один непустой `<strong>`;
- один непустой `<span>`;
- CSS-counter для нумерации.

Запрещены:

- замена `<ol>` на нейтральный `<div>`;
- ссылки, кнопки и поля внутри этапа;
- `role="button"` или `role="link"`;
- `tabindex`;
- курсор `pointer`;
- hover-transform;
- focus, pressed и selected states.

## Визуальный слой

`css/process-step-polish.css` использует только `--p36-*`:

- `surface.default`;
- `border.default`;
- `text.primary`, `text.secondary`, `text.inverse`;
- `action.primary` и `surface.accent` для номера;
- `radius.lg`, `radius.full`;
- `shadow.card`;
- spacing и typography tokens.

Старые fallback-стили остаются ниже по приоритету. Новый модуль явно сохраняет `transform: none` и `cursor: default`.

Модуль расположен после `proof-card-polish.css` и перед `logo-brand.css` в едином cache-busted production bundle.

## HowTo JSON-LD

Отдельные страницы используют schema.org `HowTo`. Визуальная миграция не изменяет JSON-LD.

Validator сопоставляет каждый найденный `HowTo` с видимым списком `.steps`, содержащим такое же количество элементов `HowToStep` и `<li>`. Страницы с несколькими независимыми процессами поддерживаются.

## Что не изменяется

- production HTML;
- тексты этапов;
- порядок этапов;
- HowTo JSON-LD;
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
python tools/check_process_step_token_migration.py
python tools/run_quality_checks.py
```
