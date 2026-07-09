# Следующие действия по проекту

Файл фиксирует только то, что нельзя полностью закрыть без ручной проверки или подтверждённых данных.

## Issue #5

Переключить `parket36.ru` на GitHub Pages.

Что осталось:

- проверить Pages source в настройках репозитория;
- проверить Custom domain;
- проверить DNS у регистратора;
- включить HTTPS после проверки домена;
- проверить успешный deploy.

Подробный чек-лист: `docs/github-pages-switch-checklist.md`.

## Issue #4

Подготовить материалы для следующего этапа сайта.

Что осталось:

- заполнить `docs/confirmed-materials-template.md`;
- собрать фото по `docs/photo-materials-checklist.md`;
- после подтверждения обновить публичные страницы сайта.

Индекс документов: `docs/materials-index.md`.

## Issue #283

Синхронизировать quality gate с отчётом по карточкам советов.

Что осталось:

- добавить `tools/report_advice_index_gaps.py` в `tools/run_quality_checks.py`;
- добавить тот же скрипт в `tools/check_quality_runner.py`;
- запустить общий quality gate.

Эта правка ранее блокировалась коннектором, поэтому задача пока оставлена отдельным issue.
