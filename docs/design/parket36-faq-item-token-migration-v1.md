# Паркет36 — production-миграция FAQ Item v1

## Цель

Перевести существующие раскрывающиеся вопросы на дизайн-токены без изменения HTML, текстов, FAQPage schema и JavaScript.

## Production scope

- страница: `voprosy-i-otvety/index.html`;
- контейнер: `.faq`;
- компонент: `.faq details`;
- trigger: `.faq summary`;
- ответ: `.faq details > p`;
- CSS: `css/typography-polish.css`.

## Контракт

Состояния:

- `closed` — вопрос закрыт, индикатор `+`;
- `open` — присутствует нативный атрибут `open`, индикатор `−`;
- `hover` — усиленная граница и тень;
- `focus` — отдельный `:focus-visible` на `<summary>`.

Размеры:

- минимальная высота trigger — 52 px;
- индикатор — 32 × 32 px;
- радиус — `radius.lg`;
- минимальная зона взаимодействия — 44 px.

## Доступность

- сохраняются нативные `<details>` и `<summary>`;
- JavaScript для открытия и закрытия не используется;
- открытое состояние отличается не только цветом, но и символом `−`;
- focus-visible заметен при клавиатурной навигации;
- `prefers-reduced-motion` отключает transition;
- вопрос и ответ остаются доступны без CSS.

## Сохранённые данные

Не изменяются:

- 16 вопросов и 16 ответов;
- четыре вопроса, открытые по умолчанию;
- заголовки тематических блоков;
- JSON-LD с типом `FAQPage`;
- ссылки, телефон и CTA;
- `js/main.js`;
- формы, аналитика, payload и Supabase.

## Figma

Целевой компонент: `FAQ Item` на странице `Foundations + Components — Дизайн-система`.

Из-за лимита Figma MCP Starter компонент записан в sync manifest как:

- `nodeId: null`;
- `status: pending`.

Это спецификация для будущего создания, а не подтверждение существующего Figma-узла.

## Проверка

```bash
python tools/check_design_component_catalog.py
python tools/check_design_foundations.py
python tools/check_faq_item_token_migration.py
python tools/run_quality_checks.py
```

После статических проверок обязательны Site quality, Lighthouse CI и Browser smoke на одном SHA.
