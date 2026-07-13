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

До type-check запускаются изолированные unit-тесты:

```bash
deno test supabase/functions/parket-public-lead/field-limits_test.ts
deno test supabase/functions/parket-public-lead/origin-policy_test.ts
deno test supabase/functions/parket-public-lead/payload-shape_test.ts
deno test supabase/functions/parket-public-lead/contact-validation_test.ts
```

Они проверяют лимиты полей, политику origin, форму JSON payload и пригодность телефона для обратного звонка.

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
- ошибка в подключении `npm:@supabase/supabase-js`;
- расхождение лимитов полей;
- нарушение origin policy;
- неправильный тип поля payload;
- контакт без телефона длиной от 10 до 15 цифр;
- удаление одного из обязательных тестов из workflow.

После Deno-проверки запускается общий Python quality gate.

## Почему проверка есть и в Pages workflow

Edge Function не публикуется через GitHub Pages, но её исходник хранится в том же репозитории. Проверка перед Pages deploy не позволяет основной ветке оставаться в состоянии, где сайт публикуется успешно, а серверная часть формы уже содержит ошибку.

## Локальный запуск

При установленном Deno:

```bash
deno test supabase/functions/parket-public-lead/field-limits_test.ts
deno test supabase/functions/parket-public-lead/origin-policy_test.ts
deno test supabase/functions/parket-public-lead/payload-shape_test.ts
deno test supabase/functions/parket-public-lead/contact-validation_test.ts
deno check supabase/functions/parket-public-lead/index.ts
```

Полная локальная проверка проекта:

```bash
python tools/run_quality_checks.py
```

Python quality gate проверяет обязательные маркеры безопасности и workflow-конфигурацию. Полноценные unit-тесты и TypeScript-проверку выполняет Deno.

## Ограничения

Тесты и `deno check` не развёртывают функцию и не выполняют запрос к боевому endpoint. После изменения Edge Function по-прежнему требуется отдельный деплой в Supabase и безопасный тест по `docs/lead-endpoint-test-mode.md`.
