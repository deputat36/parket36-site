# Паркет36 — миграция Input на токены v1

## Область

На компонент Input переведены только поля внутри `.request-form`:

- `input`;
- `select`;
- `textarea`;
- связанные `label`;
- существующие подсказки `.form-help`;
- текст ошибки, создаваемый для состояния `:user-invalid`.

Интерактивные кнопки `.pill`, кнопка отправки и статус результата формы не входят в этот этап.

## Контракт

Источник: `design/components/parket36-components.json`.

Анатомия:

- Label — существующий `<label>`;
- Field — `input`, `select` или `textarea`;
- Value — введённое или выбранное значение;
- Help — существующий `.form-help`;
- Error — текст «Проверьте обязательное поле» для `:user-invalid`.

Размеры:

- высота поля — минимум 52 px;
- горизонтальные поля — 16 px;
- радиус — `radius.md`, 14 px;
- минимальная зона взаимодействия — 44 px;
- textarea — минимум 132 px с вертикальным изменением размера.

## Состояния

### Default

Белая поверхность, нейтральная граница, основной цвет текста.

### Focus

Forest-граница и brass-50 внешнее кольцо шириной 4 px. Стандартный outline отключается только после появления равноценного видимого focus-состояния.

### Filled

Заполненные `input` и `textarea`, а также `select` получают subtle-поверхность. Значение и placeholder сохраняют разный контраст.

### Error

Обязательное поле с `:user-invalid` получает error-границу и текст «Проверьте обязательное поле». Ошибка не передаётся только цветом.

### Disabled

Поле получает нейтральную поверхность, muted-текст, `not-allowed` и пониженную непрозрачность.

## Сохранённая логика

Не изменяются:

- ID полей;
- `required`, `autocomplete`, `inputmode` и `rows`;
- значения `<option>`;
- JavaScript-обработчики;
- формирование payload;
- копирование текста;
- fallback-сценарий;
- аналитика;
- Supabase Edge Function;
- телефон и ссылки.

## Мобильное поведение

Размер текста поля остаётся 16 px, поэтому iOS не увеличивает страницу при фокусе. Поля занимают 100% ширины родительского label и не создают горизонтального переполнения на mobile 390 px.

## Проверка

```bash
python tools/check_input_token_migration.py
python tools/check_production_design_token_layer.py
python tools/run_quality_checks.py
```

После изменения обязательны Site quality, Lighthouse CI и Browser smoke, включая отправку формы, required-validation и mobile 390 px.
