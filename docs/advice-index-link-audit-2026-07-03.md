# Аудит ссылок в разделе советов

Дата проверки: 2026-07-03.

Проверка показала, что часть индексируемых страниц уже есть в `sitemap.xml`, но пока не имеет карточки в основном индексе `/sovety/`.

## Страницы без карточки

- `/sovety/kak-uhazhivat-za-parketom-vesnoy/` — добавить в блок `Сезонный уход`.
- `/sovety/kak-ponyat-chto-parket-mozhno-lakirovat/` — добавить в блок `Подготовка и покрытие`.
- `/sovety/kak-ubrat-pyl-posle-ciklevki-pered-lakom/` — добавить в блок `Подготовка и покрытие` рядом с материалами про лак.

## Следующий PR

Добавить 3 карточки в `sovety/index.html` и проверить `python tools/run_quality_checks.py`.

HTML-обновление `sovety/index.html` через connector на момент проверки блокировалось, поэтому задача зафиксирована отдельным документом.
