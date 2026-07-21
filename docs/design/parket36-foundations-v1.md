# Паркет36 — Foundations v1

## Назначение

Foundations определяют визуальную основу нового сайта: палитру, типографику, интервалы, радиусы, эффекты и сетку. Это внутренний дизайн-артефакт. Он не меняет действующий сайт и не копируется в `_site`.

Figma: https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH

Целевая страница: `Foundations + Components — Дизайн-система` (`2:4`).

## Источники

- `design/parket36-tokens.json` — значения токенов;
- `design/foundations/parket36-foundations.json` — контракт отображения и будущих Figma-стилей;
- `design/prototypes/foundations-v1.htm` — визуальный каталог;
- `design/prototypes/foundations-v1.css` — оформление каталога;
- `design/figma/parket36-sync-manifest.json` — известные Figma ID и очередь синхронизации;
- `tools/check_design_foundations.py` — fail-closed проверка.

## Цвет

В основе три семейства:

1. Neutral — фон, поверхности, текст и границы.
2. Forest — основное действие, экспертность и спокойная глубина.
3. Brass — тёплый акцент, ремесленный характер и вторичное действие.

Статусные цвета используются только для системной обратной связи. Они не заменяют текст ошибки, предупреждения или результата.

## Типографика

Заголовки: Manrope.

Основной текст: Onest.

Стили:

- `Type/Display` — 64/70, ExtraBold;
- `Type/H1` — 52/58, ExtraBold;
- `Type/H2` — 40/48, Bold;
- `Type/H3` — 28/34, Bold;
- `Type/Lead` — 20/30, Regular;
- `Type/Body` — 16/25, Regular;
- `Type/Body Strong` — 16/25, SemiBold;
- `Type/Small` — 14/21, Regular;
- `Type/Eyebrow` — 12/18, Bold, uppercase, tracking 14%.

Перед созданием или изменением текста в Figma необходимо загрузить точный шрифт и стиль через `loadFontAsync`.

## Интервалы и формы

Шкала интервалов: 0, 4, 8, 12, 16, 24, 32, 48, 64 и 96 px.

Радиусы: 0, 8, 14, 20, 28 и 999 px.

Минимальная зона взаимодействия — 44 px.

## Эффекты

- `Effect/Card` — спокойные карточки и панели;
- `Effect/Floating` — плавающие CTA и важные подсказки.

Тени не используются как декоративный эффект на каждом блоке. Иерархия в первую очередь строится фоном, границей, расстоянием и типографикой.

## Сетка

Desktop:

- холст 1440 px;
- контейнер 1180 px;
- 12 колонок;
- gutter 24 px;
- ориентировочные внешние поля 130 px.

Mobile:

- холст 390 px;
- 4 колонки;
- gutter 16 px;
- поля 20 px.

## Правила переноса в Figma

1. Не создавать новые страницы: Starter-файл уже использует три доступные страницы.
2. Foundations и компоненты размещать секциями на странице `2:4`.
3. Все существующие переменные сначала аудировать по имени, типу, scope, alias и WEB code syntax.
4. Семантические переменные должны ссылаться на primitives, а не дублировать значения.
5. Создать девять text styles и два effect styles из контракта.
6. Каждый созданный или изменённый node ID записать в sync manifest.
7. После каждого раздела проверить metadata и screenshot.
8. До повторной Figma-верификации статус остаётся `draft` или `partial-unverified`.

## Проверка

```bash
python tools/build_design_token_css.py --check
python tools/check_design_foundations.py
```
