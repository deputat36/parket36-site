# Защита production workflow основной веткой

## Назначение

Production-workflow могут обращаться к Supabase, читать признаки наличия GitHub secrets, обновлять monitoring issues или создавать контролируемую техническую заявку. Поэтому ручной запуск из feature-ветки не должен доходить даже до checkout и подготовки job.

Для этого защищённый job содержит точное условие:

```yaml
if: github.ref_name == github.event.repository.default_branch
```

При запуске не из default branch job получает статус `skipped`. Шаги не начинаются, checkout не выполняется, production secrets не подключаются к окружению job и внешние production-проверки не вызываются.

## Защищённые workflow

- `.github/workflows/production-lead-launch-readiness.yml` — защищён job `readiness`;
- `.github/workflows/deploy-lead-function.yml` — защищён job `validate`;
- `.github/workflows/controlled-lead-smoke.yml` — защищён job `validate`;
- `.github/workflows/lead-endpoint-health.yml` — защищён job `health`.

В workflow развёртывания и controlled smoke второй job зависит от защищённого первого job через:

```yaml
needs: validate
```

Если validation-job был пропущен из-за посторонней ветки, deploy или отправка контролируемой заявки также не выполняются.

## Зачем сохраняются внутренние проверки ветки

В deploy, readiness и controlled smoke остаются повторные shell-проверки текущей ветки. Job-level guard останавливает запуск до подготовки runner, а внутренняя проверка остаётся вторым независимым fail-closed уровнем на случай ошибочного изменения структуры workflow.

## CI-контракт

Проверка выполняется командой:

```bash
python tools/check_production_default_branch_guards.py
```

Она требует:

- ровно один job-level guard в каждом защищённом workflow;
- размещение guard до `runs-on`, `env` и `steps`;
- наличие guard именно в первом защищённом job;
- зависимость `needs: validate` для deploy и controlled smoke;
- наличие этого документа и описания всех четырёх workflow.

Самопроверка:

```bash
python tools/check_production_default_branch_guards.py --self-test
```

Quality gate запускает контракт до production-специфичных проверок. Удаление или перенос guard должно блокировать PR и Pages build.

## Границы

Изменение не развёртывает Edge Functions, не создаёт заявку, не меняет secrets и не вызывает production endpoint. Оно только фиксирует и проверяет уже действующее правило запуска из default branch.
