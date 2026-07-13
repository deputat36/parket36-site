# Cache-busting проверки deployment.json

`/deployment.json` создаётся только внутри GitHub Pages artifact `_site` и используется для подтверждения источника и точной версии публикации.

## Почему нужен cache-busting

Сразу после `Deploy GitHub Pages` разные точки CDN могут кратковременно отдавать предыдущую версию статического файла. Формально корректный, но старый manifest не должен считаться актуальным deploy и не должен преждевременно закрывать issue #5.

Post-deploy проверка поэтому запрашивает manifest с query-параметрами:

- `verify_commit` — ожидаемый SHA опубликованного коммита;
- `verify_run` — ID завершившегося Pages workflow;
- `attempt` — номер текущей попытки.

Каждая повторная попытка получает новый URL-кэш-ключ. Дополнительно отправляются заголовки:

```text
Cache-Control: no-cache, no-store, max-age=0
Pragma: no-cache
```

Query-параметры не изменяют содержимое статического файла и не публикуются как отдельные страницы. В диагностическом отчёте показывается canonical URL без query:

```text
https://parket36.ru/deployment.json
```

## Различие режимов

Ежедневная и ручная проверка используют чистый canonical URL, потому что подтверждают общий источник публикации без требования конкретной версии.

Post-deploy проверка использует cache-busting URL и требует точного совпадения:

```text
manifest.commit == workflow_run.head_sha
manifest.run_id == workflow_run.id
```

До шести попыток выполняются с интервалом 10 секунд. Если точная версия не появилась, проверка завершается ошибкой и сохраняет live-health report.

## Что считается ошибкой

- `/deployment.json` отсутствует;
- publisher отличается от `github-actions`;
- artifact отличается от `_site`;
- SHA не совпадает с опубликованным commit;
- run ID не совпадает с завершившимся Pages deploy;
- после всех попыток CDN продолжает отдавать предыдущую сборку.

Issue #5 закрывается только после успешной точной проверки. Cache-busting снижает риск ложного сбоя из-за промежуточного CDN-кэша, но не скрывает реальную ошибку DNS, Pages settings или публикации.

## Проверка

```bash
python tools/check_live_deployment.py --self-test
python tools/check_post_deploy_verification.py
```
