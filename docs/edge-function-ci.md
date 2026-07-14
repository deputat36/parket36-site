# Проверка Edge Functions в GitHub Actions

Исходники функций:

```text
supabase/functions/parket-public-lead/index.ts
supabase/functions/parket-lead-verify/index.ts
```

`parket-public-lead` принимает заявки. `parket-lead-verify` используется только защищённым workflow контролируемой production-проверки и возвращает факт наличия строки лида и принятой audit-записи.

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
deno test supabase/functions/parket-lead-verify/request-id_test.ts
```

Они проверяют:

- лимиты полей публичной заявки;
- политику origin;
- форму JSON payload;
- пригодность телефона для обратного звонка;
- безопасный формат request ID контролируемой заявки.

Затем запускаются:

```bash
deno check supabase/functions/parket-public-lead/index.ts
deno check supabase/functions/parket-lead-verify/index.ts
```

## Что блокируется

PR или Pages-сборка не проходят, если в любой Edge Function есть:

- синтаксическая ошибка TypeScript;
- несовместимый тип;
- ошибка разрешения импортов;
- некорректное использование API Deno;
- ошибка в подключении `npm:@supabase/supabase-js`;
- расхождение лимитов полей;
- нарушение origin policy;
- неправильный тип поля payload;
- контакт без телефона длиной от 10 до 15 цифр;
- небезопасный request ID verifier;
- удаление одного из обязательных тестов или type-check из workflow.

После Deno-проверки запускается общий Python quality gate. Отдельный `tools/check_controlled_lead_smoke.py` требует присутствия verifier-тестов и type-check одновременно в `Site quality`, `Deploy GitHub Pages` и ручном deploy-workflow.

## Почему проверка есть в Pages workflow

Edge Functions не публикуются через GitHub Pages, но их исходники хранятся в том же репозитории. Проверка перед Pages deploy не позволяет основной ветке оставаться в состоянии, где сайт публикуется успешно, а серверная часть формы или verifier уже содержит ошибку.

## Ручной deploy

Обе функции разворачиваются только workflow `Deploy production lead function`:

1. сначала `parket-lead-verify`;
2. затем `parket-public-lead`;
3. после этого public preflight и protected healthcheck.

Само наличие зелёного CI не означает, что production Supabase уже обновлён.

## Контролируемая заявка

После зелёного deploy отдельный workflow `Controlled production lead smoke`:

- создаёт одну реальную техническую заявку;
- проверяет ответ публичной функции;
- вызывает verifier по точному request ID;
- подтверждает `parket_leads` и `parket_public_lead_audit`;
- не выводит контакт или health-токен.

Фактическое получение уведомления Иваном подтверждается вручную.

## Локальный запуск

При установленном Deno:

```bash
deno test supabase/functions/parket-public-lead/field-limits_test.ts
deno test supabase/functions/parket-public-lead/origin-policy_test.ts
deno test supabase/functions/parket-public-lead/payload-shape_test.ts
deno test supabase/functions/parket-public-lead/contact-validation_test.ts
deno test supabase/functions/parket-lead-verify/request-id_test.ts
deno check supabase/functions/parket-public-lead/index.ts
deno check supabase/functions/parket-lead-verify/index.ts
```

Полная локальная проверка проекта:

```bash
python tools/run_quality_checks.py
```

Python quality gate проверяет обязательные маркеры безопасности, workflow-конфигурацию и self-tests. Полноценные unit-тесты и TypeScript-проверку выполняет Deno.

## Ограничения

- тесты и `deno check` не развёртывают функции;
- CI не выполняет реальную production-заявку;
- deploy требует настроенных secrets и ручного подтверждения;
- controlled smoke создаёт реальную запись и запускается только после зелёного deploy;
- после технического PASS всё равно требуется ручное подтверждение уведомления Иваном.
