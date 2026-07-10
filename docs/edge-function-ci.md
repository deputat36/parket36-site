# Проверка Edge Function в GitHub Actions

Исходник функции:

```text
supabase/functions/parket-public-lead/index.ts
```

## Что выполняется

Workflow `Site quality` и `Deploy GitHub Pages` устанавливают Deno через:

```yaml
uses: denoland/setup-deno@v2
with:
  deno-version: lts
```

Затем запускается:

```bash
deno check supabase/functions/parket-public-lead/index.ts
```

## Что блокируется

PR или Pages-сборка не проходят, если в Edge Function есть:

- синтаксическая ошибка TypeScript;
- несовместимый тип;
- ошибка разрешения импортов;
- некорректное использование API Deno;
- ошибка в подключении `npm:@supabase/supabase-js`.

После Deno-проверки запускается общий Python quality gate.

## Почему проверка есть и в Pages workflow

Edge Function не публикуется через GitHub Pages, но её исходник хранится в том же репозитории. Проверка перед Pages deploy не позволяет основной ветке оставаться в состоянии, где сайт публикуется успешно, а серверная часть формы уже содержит ошибку.

## Локальный запуск

При установленном Deno:

```bash
deno check supabase/functions/parket-public-lead/index.ts
```

Полная локальная проверка проекта:

```bash
python tools/run_quality_checks.py
```

Python quality gate проверяет обязательные маркеры безопасности и workflow-конфигурацию. Полноценную TypeScript-проверку выполняет Deno.

## Ограничения

`deno check` не развёртывает функцию и не выполняет запрос к боевому endpoint. После изменения Edge Function по-прежнему требуется отдельный деплой в Supabase и безопасный тест по `docs/lead-endpoint-test-mode.md`.
