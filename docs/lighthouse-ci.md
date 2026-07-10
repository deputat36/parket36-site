# Lighthouse CI для Паркет36

Дата обновления: 2026-07-10.

Workflow: `.github/workflows/lighthouse.yml`.

Конфигурация: `lighthouserc.cjs`.

## Проверяемые страницы

- главная `/`;
- форма оценки `/zayavka/`.

Проверка запускается против локально собранной папки `_site`, поэтому не зависит от DNS, GitHub Pages и production Supabase.

## Категории и пороги

- Performance: предупреждение при результате ниже `0.65`;
- Accessibility: ошибка при результате ниже `0.90`;
- Best Practices: предупреждение при результате ниже `0.85`;
- SEO: ошибка при результате ниже `0.90`.

Производительность и Best Practices сначала используются как измеряемый baseline: результат сохраняется, но единичное ухудшение ниже порога не блокирует публикацию. Accessibility и SEO блокируют PR при падении ниже минимального уровня.

## Запуск

Workflow запускается:

- для каждого Pull Request;
- после изменения `main`;
- еженедельно;
- вручную через `workflow_dispatch`.

Локально:

```bash
npm install --no-audit --no-fund
python tools/build_pages.py
npm run test:lighthouse
```

## Отчёты

Lighthouse сохраняет HTML и JSON в `lighthouse-report`. GitHub Actions загружает папку как artifact `lighthouse-report` на 30 дней.

## Дальнейшая работа

После нескольких стабильных запусков можно повышать порог Performance небольшими шагами. Сначала необходимо устранить подтверждённые тяжёлые ресурсы, лишние CSS-подключения и блокирующие загрузку элементы, а не искусственно отключать полезные проверки Lighthouse.
