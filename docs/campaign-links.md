# Измеряемые ссылки запуска Паркет36

Файл генерируется из `data/campaign-links.json` командой `python tools/build_campaign_links.py --write`.
Проверка актуальности входит в общий quality gate: `python tools/build_campaign_links.py --check`.

Единая кампания: `voronezh_parquet_launch`.

## Готовые ссылки

| Размещение | Назначение | Посадочная | Измеряемая ссылка |
|---|---|---|---|
| VK — главная страница | Общий пост о мастере и восстановлении паркета | `/` | `https://parket36.ru/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=organic_post_home` |
| VK — циклёвка паркета | Пост или обсуждение конкретной услуги | `/uslugi/ciklevka-parketa/` | `https://parket36.ru/uslugi/ciklevka-parketa/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=organic_post_cyclevka` |
| VK — обратный звонок | Публикация с прямым переходом к короткой форме обратного звонка | `/kontakty/#callback` | `https://parket36.ru/kontakty/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=callback_post#callback` |
| Авито — циклёвка паркета | Ссылка из объявления по циклёвке и шлифовке | `/uslugi/ciklevka-parketa/` | `https://parket36.ru/uslugi/ciklevka-parketa/?utm_source=avito&utm_medium=classified&utm_campaign=voronezh_parquet_launch&utm_content=service_listing_cyclevka` |
| Яндекс Бизнес — контакты | Ссылка из локальной карточки после её подтверждения | `/kontakty/` | `https://parket36.ru/kontakty/?utm_source=yandex_business&utm_medium=local&utm_campaign=voronezh_parquet_launch&utm_content=business_profile` |
| 2ГИС — контакты | Ссылка из локальной карточки после её подтверждения | `/kontakty/` | `https://parket36.ru/kontakty/?utm_source=2gis&utm_medium=local&utm_campaign=voronezh_parquet_launch&utm_content=business_profile` |
| QR на листовке — оценка по фото | QR-код на листовке, визитке или печатном объявлении | `/zayavka/` | `https://parket36.ru/zayavka/?utm_source=offline&utm_medium=qr&utm_campaign=voronezh_parquet_launch&utm_content=flyer_photo_estimate` |

## Как использовать

- размещать готовую ссылку только в указанном канале, не заменяя её обычной ссылкой на домен;
- для нового объявления или макета добавлять отдельный `content`, чтобы обращения не смешивались;
- QR-код создавать именно из полной ссылки с UTM-параметрами;
- для ссылки с якорем сохранять порядок `?utm_...#callback`: query перед fragment;
- после восстановления домена сначала открыть каждую ссылку вручную и убедиться, что посадочная страница загружается по HTTPS;
- не публиковать ссылки на ещё не созданные карточки: строки для Яндекс Бизнеса и 2ГИС подготовлены заранее, но используются только после подтверждения соответствующей карточки.

## Прямая ссылка на обратный звонок

Ссылка `VK — обратный звонок` открывает `/kontakty/#callback` сразу на короткой форме. Генератор проверяет, что целевая страница существует и содержит элемент `id="callback"`. UTM остаются в query-параметрах до `#callback`, поэтому first-touch атрибуция сохраняется до отправки заявки.

## Что уже измеряется

Сайт сохраняет первую UTM-атрибуцию в пределах сессии и передаёт `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` и `utm_term` вместе с заявкой. Поэтому источник заявки по форме можно определить даже до подключения Яндекс Метрики, если production Edge Function развёрнута и сохраняет актуальный payload.

Клик по телефону отправляется как аналитическое событие только после подключения счётчика. До этого звонки нельзя надёжно связать с конкретной UTM-ссылкой средствами самого сайта.

## Ограничения

Готовые ссылки не создают рекламу, карточки или объявления автоматически. Они дают единый формат атрибуции для ручных размещений и не заменяют доступный домен, аналитику, подтверждённые фотографии и фактическую обработку обращений.
