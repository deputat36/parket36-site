# CSS bundle и cache busting

Дата обновления: 2026-07-21.

## Цель

Публичная сборка Паркет36 должна загружать одну таблицу стилей вместо отдельных CSS-модулей. Первый модуль содержит production-копию дизайн-токенов, остальные сохраняют действующее оформление и постепенно переводятся на токены отдельными PR.

## Исходные файлы

Читаемые модули остаются в каталоге `css/`:

1. `design-tokens.css`;
2. `style.css`;
3. `enhancements.css`;
4. `photo-brief.css`;
5. `interface-polish.css`;
6. `mobile-menu.css`;
7. `typography-polish.css`;
8. `scroll-progress.css`;
9. `accessibility-polish.css`;
10. `cta-polish.css`;
11. `logo-brand.css`.

Порядок задаётся константой `CSS_MODULES` в `tools/css_bundle.py`. Он важен, потому что более поздние модули могут уточнять базовые стили.

`design-tokens.css` всегда располагается первым. Он генерируется из `design/parket36-tokens.json` и не редактируется вручную.

## Публичная сборка

`python tools/build_pages.py` выполняет следующие действия:

1. копирует публичные HTML, JavaScript и изображения в `_site`;
2. объединяет CSS-модули в заданном порядке;
3. вычисляет первые 12 символов SHA-256 содержимого;
4. создаёт файл вида `_site/css/site.<hash>.css`;
5. заменяет все исходные CSS-ссылки в собранном HTML одной ссылкой;
6. удаляет runtime-подключение CSS из production-копии `js/main.js`;
7. проверяет, что в `_site/css` остался ровно один CSS-файл.

Исходные HTML и `js/main.js` не переписываются. Поэтому файлы остаются удобными для локального просмотра и дальнейшего редактирования.

## Cache busting

Имя bundle зависит от его содержимого. При любом изменении CSS меняется URL файла, поэтому браузер не использует устаревший кэш.

Не нужно вручную изменять номер версии или query-параметр.

## Автоматические проверки

Сборка завершается ошибкой, если:

- отсутствует любой обязательный CSS-модуль;
- production-копия токенов расходится с дизайн-копией;
- `design-tokens.css` находится не первым в `CSS_MODULES`;
- HTML не содержит исходной CSS-ссылки для замены;
- отсутствует `</head>`;
- в публичной папке находится больше одного CSS-файла;
- HTML ссылается не на один bundle;
- production `main.js` продолжает загружать CSS через JavaScript.

После изменения CSS дополнительно выполняются Playwright, axe и Lighthouse CI.

## Локальная проверка

```bash
python tools/build_design_token_css.py --check
python tools/check_production_design_token_layer.py
python tools/build_pages.py
```

После успешной сборки:

- в `_site/css/` должен быть один файл `site.<hash>.css`;
- в начале bundle должен находиться блок `source: css/design-tokens.css`;
- в каждом HTML должен быть атрибут `data-css-bundle="true"`;
- в `_site/js/main.js` не должно быть вызовов `ensureStylesheet('/css/...')`.
