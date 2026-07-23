# Паркет36 — production-миграция Breadcrumbs v1

## Назначение

Breadcrumbs помогают пользователю понять положение страницы в структуре сайта и вернуться к родительскому разделу. Компонент уже используется на внутренних страницах и является источником для build-time генерации schema.org `BreadcrumbList`.

## Production scope

Изменяется только визуальный слой `.breadcrumbs` через `css/breadcrumbs-polish.css`.

Не изменяются:

- HTML-анатомия публичных страниц;
- тексты пунктов;
- порядок ссылок;
- адреса ссылок;
- разделитель `›`;
- текущий пункт без ссылки;
- `tools/breadcrumb_schema.py`;
- `tools/check_breadcrumb_schema.py`;
- canonical URL;
- маршруты;
- JavaScript;
- формы, payload, аналитика, Supabase и backend.

## Анатомия

1. `Container` — `.breadcrumbs`.
2. `Link` — один или несколько родительских пунктов.
3. `Separator` — текстовый символ `›`.
4. `Current` — последний `<span>` без ссылки.

Первым пунктом остаётся ссылка «Главная» с `href="/"`.

## Состояния

- `default` — спокойная цепочка на светлой поверхности;
- `hover` — ссылка получает subtle surface и подчёркивание;
- `focus` — ссылка получает отдельное brass-кольцо и accent surface.

Текущий пункт визуально отличается от разделителей и не становится ссылкой.

## Размеры

- минимальная высота контейнера — 40 px;
- горизонтальные поля — 12 px;
- gap — 8 px;
- desktop radius — `radius.full`;
- mobile до 640 px — `radius.md` и ширина 100%;
- цепочка использует `flex-wrap: wrap` и не обрезается по ширине.

## Токены

Используются только `--p36-*`:

- `surface.default`;
- `surface.subtle`;
- `surface.accent`;
- `border.default`;
- `text.primary`;
- `text.muted`;
- `text.accent`;
- `action.primary.hover`;
- `primitive.brass.200`;
- `spacing.sm` и `spacing.md`;
- `radius.sm`, `radius.md`, `radius.full`;
- `shadow.card`;
- `font.weight.semibold` и `font.weight.bold`.

Raw HEX, RGB/HSL и legacy `--wood`/`--gold` в новом модуле запрещены.

## BreadcrumbList

Видимая цепочка остаётся источником для `BreadcrumbList`. Validator обязан подтверждать:

- первый пункт — «Главная»;
- последний пункт — текст без ссылки;
- между пунктами используются разделители `›`;
- ссылки имеют непустой текст и `href`;
- существующий self-test `tools/check_breadcrumb_schema.py` остаётся в общем quality gate;
- `tools/breadcrumb_schema.py` и публичные HTML не изменяются в этой миграции.

## Figma

Целевой файл: `https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH`.

Компонент записан в sync manifest как:

- `nodeId: null`;
- `status: pending`.

До восстановления лимита Figma MCP реальный компонент не считается созданным.

## Проверка

```bash
python tools/check_breadcrumbs_token_migration.py
python tools/check_breadcrumb_schema.py
python tools/run_quality_checks.py
```

После изменений обязательны Site quality, Lighthouse и Browser smoke.
