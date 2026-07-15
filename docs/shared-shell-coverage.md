# Покрытие shared shell

Файл генерируется командой `python tools/build_shared_shell_coverage.py --output-dir reports/shared-shell-coverage`.
Отчёт показывает, какие публичные HTML-страницы используют явный или семейный профиль общей оболочки, а какие пока остаются вне shared shell.

## Сводка

- публичных HTML-страниц: 107;
- страниц с профилем shared shell: 94;
- страниц вне shared shell: 13;
- покрытие: 87.9%.

Страница вне shared shell не считается автоматической ошибкой: отчёт нужен для осознанного выбора следующего однородного семейства и для обнаружения новых непрофилированных страниц.

## Источники профилей

| Источник | Страниц |
|---|---:|
| `explicit` | 19 |
| `family:articles` | 70 |
| `family:solutions` | 5 |
| вне shared shell | 13 |

## Страницы вне shared shell

| URL | Исходный файл |
|---|---|
| `/404.html` | `404.html` |
| `/politika/` | `politika/index.html` |
| `/pozvonit-ivanu/` | `pozvonit-ivanu/index.html` |
| `/uslugi/demontazh/` | `uslugi/demontazh/index.html` |
| `/uslugi/elektrika/` | `uslugi/elektrika/index.html` |
| `/uslugi/master-na-chas/` | `uslugi/master-na-chas/index.html` |
| `/uslugi/melkiy-remont/` | `uslugi/melkiy-remont/index.html` |
| `/uslugi/muzh-na-chas/` | `uslugi/muzh-na-chas/index.html` |
| `/uslugi/otdelka/` | `uslugi/otdelka/index.html` |
| `/uslugi/pereezdy/` | `uslugi/pereezdy/index.html` |
| `/uslugi/santehnika/` | `uslugi/santehnika/index.html` |
| `/uslugi/sborka-mebeli/` | `uslugi/sborka-mebeli/index.html` |
| `/uslugi/vyvoz-musora/` | `uslugi/vyvoz-musora/index.html` |

## Полные данные

Artifact `shared-shell-coverage` содержит:

- `shared-shell-coverage.csv` — классификацию каждой публичной HTML-страницы;
- `shared-shell-coverage.md` — этот отчёт с актуальной сводкой.
