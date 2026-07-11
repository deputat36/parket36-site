# Карта внутренних ссылок Паркет36

Файл генерируется командой `python tools/build_internal_link_map.py --output-dir reports/internal-links`.
Контекстными считаются ссылки внутри `<main>`; ссылки общей шапки, футера и мобильной панели учитываются только в полном графе.

## Сводка

- индексируемых страниц: 94;
- уникальных внутренних связей во всём HTML: 1408;
- уникальных контекстных связей внутри `<main>`: 818;
- страниц без контекстных входящих ссылок: 3;
- страниц с 0–1 контекстной входящей ссылкой: 16;
- страниц, зависящих только от общих элементов: 3;
- страниц, недостижимых от главной по контекстным ссылкам: 3;
- страниц, недостижимых от главной по любым внутренним ссылкам: 0.

Порог низкой связности является сигналом для редакторской проверки, а не автоматическим требованием добавить ссылку.

## Страницы с низкой контекстной связностью

| URL | Раздел | Контекстные входящие | Все входящие | Контекстная глубина | Только общие элементы |
|---|---|---:|---:|---:|:---:|
| https://parket36.ru/voprosy-i-otvety/ | voprosy-i-otvety | 0 | 2 | — | да |
| https://parket36.ru/kontakty/ | kontakty | 0 | 93 | — | да |
| https://parket36.ru/o-mastere/ | o-mastere | 0 | 93 | — | да |
| https://parket36.ru/sovety/kak-proverit-shlifovku-parketa-pered-lakom/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/kak-uhazhivat-za-parketom-vesnoy/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/mozhno-li-ciklevat-krashenyy-derevyannyy-pol/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/mozhno-li-ciklevat-parketnuyu-dosku/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/mozhno-li-zhit-v-kvartire-vo-vremya-ciklevki-parketa/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/nuzhno-li-snimat-plintusy-pered-ciklevkoy-parketa/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/pochemu-lak-na-parkete-treskaetsya-posle-lakirovki/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/pochemu-parket-stal-skolzkim-posle-lakirovki/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/shcheli-posle-ciklevki-parketa/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/sovety/sledy-ot-zhivotnyh-na-parkete/ | sovety | 1 | 1 | 3 | нет |
| https://parket36.ru/uslugi/terrasy-i-derevyannye-poly/ | uslugi | 1 | 1 | 2 | нет |
| https://parket36.ru/kak-rabotaem/ | kak-rabotaem | 1 | 3 | 1 | нет |
| https://parket36.ru/portfolio/ | portfolio | 1 | 93 | 4 | нет |

## Главные получатели контекстных ссылок

| URL | Контекстные входящие | Все входящие |
|---|---:|---:|
| https://parket36.ru/zayavka/ | 92 | 92 |
| https://parket36.ru/sovety/ | 70 | 93 |
| https://parket36.ru/sovety/kak-sfotografirovat-pol-dlya-ocenki/ | 30 | 34 |
| https://parket36.ru/uslugi/restavraciya-parketa/ | 26 | 32 |
| https://parket36.ru/uslugi/ciklevka-parketa/ | 25 | 76 |
| https://parket36.ru/sovety/skolko-sohnet-lak-na-parkete/ | 25 | 25 |
| https://parket36.ru/sovety/parket-posle-vody/ | 22 | 22 |
| https://parket36.ru/sovety/uhod-za-parketom-posle-ciklevki/ | 20 | 20 |
| https://parket36.ru/sovety/pochemu-skripit-parket/ | 19 | 19 |
| https://parket36.ru/sovety/shcheli-v-parkete/ | 18 | 18 |
| https://parket36.ru/sovety/lak-ili-maslo-dlya-parketa/ | 16 | 17 |
| https://parket36.ru/sovety/staryy-lak-na-parkete/ | 15 | 15 |
| https://parket36.ru/uslugi/pokrytie-lakom-i-maslom/ | 13 | 46 |
| https://parket36.ru/uslugi/parket-i-poly/ | 13 | 22 |
| https://parket36.ru/sovety/kak-podgotovit-komnatu-k-ciklevke/ | 13 | 15 |

## Главные контекстные хабы

| URL | Контекстные исходящие | Все исходящие |
|---|---:|---:|
| https://parket36.ru/sovety/ | 75 | 81 |
| https://parket36.ru/uslugi/parket-i-poly/ | 14 | 18 |
| https://parket36.ru/ | 12 | 17 |
| https://parket36.ru/uslugi/ | 11 | 17 |
| https://parket36.ru/sovety/kak-ponyat-chto-parket-mozhno-lakirovat/ | 10 | 17 |
| https://parket36.ru/sovety/kogda-mozhno-stelit-kover-posle-lakirovki-parketa/ | 10 | 17 |
| https://parket36.ru/sovety/pochemu-lak-na-parkete-beleet-posle-lakirovki/ | 10 | 17 |
| https://parket36.ru/sovety/pochemu-lak-na-parkete-puzyritsya-posle-lakirovki/ | 10 | 17 |
| https://parket36.ru/sovety/pochemu-lak-na-parkete-pyatnami-posle-lakirovki/ | 10 | 17 |
| https://parket36.ru/uslugi/ciklevka-parketa/ | 10 | 17 |
| https://parket36.ru/sovety/belye-pyatna-na-parkete/ | 10 | 16 |
| https://parket36.ru/sovety/mozhno-li-pokryt-parket-lakom-bez-ciklevki/ | 10 | 15 |
| https://parket36.ru/sovety/nuzhna-li-mezhsloynaya-shlifovka-laka-na-parkete/ | 10 | 15 |
| https://parket36.ru/uslugi/restavraciya-parketa/ | 9 | 17 |
| https://parket36.ru/sovety/kak-provetrivat-komnatu-posle-lakirovki-parketa/ | 9 | 16 |

## Связи между разделами

| Из раздела \ В раздел | ceny | home | kak-rabotaem | kontakty | o-mastere | portfolio | resheniya | sovety | uslugi | voprosy-i-otvety | zayavka |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ceny | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| home | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 3 | 7 | 0 | 0 |
| kak-rabotaem | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 1 |
| kontakty | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 1 |
| o-mastere | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 2 | 0 | 1 |
| portfolio | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| resheniya | 0 | 6 | 0 | 0 | 0 | 0 | 16 | 2 | 3 | 0 | 6 |
| sovety | 1 | 70 | 0 | 0 | 0 | 1 | 3 | 467 | 51 | 0 | 71 |
| uslugi | 5 | 9 | 0 | 0 | 0 | 0 | 0 | 18 | 32 | 0 | 9 |
| voprosy-i-otvety | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 1 |
| zayavka | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Полные данные

Artifact `internal-link-map` содержит:

- `internal-link-nodes.csv` — показатели каждой индексируемой страницы;
- `internal-link-edges.csv` — контекстные связи и тексты анкоров;
- `internal-link-map.md` — этот отчёт с полной актуальной сводкой.
