# Аналитика звонков и заявок Паркет36

Дата обновления: 2026-07-14.

Документ описывает события, которые уже есть на сайте `parket36.ru`, и порядок подключения целей в Яндекс.Метрике или GTM.

## Главная цель

Главное бизнес-действие сайта — звонок Ивану по номеру `8 (900) 926-79-29`.

Форма `/zayavka/` остаётся вторым важным действием: она сохраняет заявку через Supabase Edge Function и дополнительно копирует готовый текст, чтобы клиент мог приложить фотографии пола отдельными сообщениями.

Сохранение заявки и подтверждение автоматического уведомления Ивану — разные технические факты. Их нельзя считать одной метрикой.

## Что уже делает `js/main.js`

Скрипт собирает UTM-атрибуцию при первом визите и сохраняет её в `sessionStorage` под ключом `parket36_attribution`.

В атрибуцию попадают:

- `source` — `utm_source`, referrer host или `direct`;
- `medium` — `utm_medium`;
- `campaign` — `utm_campaign`;
- `content` — `utm_content`;
- `term` — `utm_term`;
- `landing` — первая страница входа;
- `firstSeen` — время первого визита в ISO-формате.

Все лид-события отправляются как браузерное событие:

```js
window.addEventListener('parket36:lead', event => {
  console.log(event.detail);
});
```

## События лидогенерации

| Событие | Когда срабатывает | Зачем нужно |
|---|---|---|
| `phone` | Клик по обычной ссылке `tel:` | Основная цель звонка |
| `phone-inline` | Клик по телефону в динамическом inline-блоке | Отдельно показывает эффективность вставных CTA |
| `request-open` | Клик по ссылке на форму или `/zayavka/` | Показывает интерес к оценке по фото |
| `request-inline` | Клик по заявке в динамическом inline-блоке | Показывает эффективность вставного блока |
| `request-template` | Выбор шаблона задачи в форме | Показывает, какие сценарии выбирают клиенты |
| `request-submit` | Backend подтвердил сохранение заявки в Supabase | Главная цель формы, но не подтверждение доставки уведомления Ивану |
| `request-copy` | Автосохранение не прошло, но текст подготовлен или скопирован | Важный fallback, клиент всё ещё может связаться вручную |

## Состояние уведомления

После `request-submit` модуль `js/lead-notification-feedback.js` создаёт отдельное событие:

```js
window.addEventListener('parket36:lead-notification', event => {
  console.log(event.detail);
});
```

Поле `notification` принимает:

- `sent` — настроенный канал или каналы подтвердили отправку;
- `disabled` — каналы уведомления не настроены;
- `partial_failure` — хотя бы один настроенный канал не подтвердил отправку;
- `unknown` — старая или неизвестная версия ответа backend.

`notificationConfirmed: true` возможно только при `notification: sent`.

Состояния `disabled`, `partial_failure` и `unknown` не отменяют сохранение заявки, но сайт рекомендует посетителю сразу позвонить Ивану.

## Отдельное событие звонка

Для звонков добавлено отдельное браузерное событие:

```js
window.addEventListener('parket36:phone-click', event => {
  console.log(event.detail);
});
```

Оно срабатывает для `phone` и `phone-inline`.

В `event.detail` передаются:

- `type` — `phone` или `phone-inline`;
- `href` — телефонная ссылка;
- `page` — текущая страница;
- `attribution` — источник, кампания, страница входа и UTM.

## Подключение Яндекс.Метрики

Сайт уже умеет отправлять цели в Метрику, если на странице есть:

```js
window.parket36MetrikaId = 12345678;
```

и подключён стандартный счётчик Метрики, который создаёт функцию `window.ym`.

После этого скрипты сайта отправят:

```js
ym(12345678, 'reachGoal', 'phone-click', payload);
ym(12345678, 'reachGoal', 'phone', payload);
ym(12345678, 'reachGoal', 'phone-inline', payload);
ym(12345678, 'reachGoal', 'request-open', payload);
ym(12345678, 'reachGoal', 'request-submit', payload);
ym(12345678, 'reachGoal', 'request-copy', payload);
ym(12345678, 'reachGoal', 'callback-open', payload);
ym(12345678, 'reachGoal', 'callback-request', payload);
ym(12345678, 'reachGoal', 'lead-notification', payload);
```

Рекомендуемые цели в Метрике:

| Цель | Тип | Комментарий |
|---|---|---|
| `phone-click` | JavaScript-событие | Главная звонковая цель |
| `request-submit` | JavaScript-событие | Заявка сохранена в Supabase |
| `lead-notification` | JavaScript-событие | Состояние автоматического уведомления Ивану |
| `request-open` | JavaScript-событие | Интерес к подробной форме |
| `callback-open` | JavaScript-событие | Интерес к короткой форме |
| `callback-request` | JavaScript-событие | Callback-заявка сохранена |
| `request-copy` | JavaScript-событие | Fallback при сбое сохранения |
| `request-template` | JavaScript-событие | Диагностика сценариев задач |

Для бизнес-анализа нельзя считать `request-submit` доказательством, что Иван уже получил или прочитал уведомление. Для этого использовать `lead-notification` и поле `notification_confirmed`.

## Подключение GTM / dataLayer

При клике по телефону добавляется событие:

```js
{
  event: 'parket36_phone_click',
  phone_href: 'tel:+79009267929',
  page: '/...',
  attribution: {
    source: '...',
    medium: '...',
    campaign: '...',
    content: '...',
    term: '...',
    landing: '/...',
    firstSeen: '...'
  }
}
```

Для состояния уведомления добавляется:

```js
{
  event: 'parket36_lead_notification',
  notification_state: 'sent' | 'disabled' | 'partial_failure' | 'unknown',
  notification_confirmed: true | false,
  duplicate: false,
  form_kind: 'assessment' | 'callback',
  page: '/...',
  service: '...',
  attribution: {}
}
```

Для callback-заявки `parket36_callback_request` также содержит `notification_state`, `notification_confirmed` и `duplicate`.

В GTM нужны отдельные триггеры Custom Event:

```text
parket36_phone_click
parket36_lead_notification
parket36_callback_request
```

## Как проверить вручную

Откройте сайт в браузере, затем в консоли выполните:

```js
window.addEventListener('parket36:phone-click', event => console.log('phone-click', event.detail));
window.addEventListener('parket36:lead', event => console.log('lead', event.detail));
window.addEventListener('parket36:lead-notification', event => console.log('lead-notification', event.detail));
```

После клика по телефону должны появиться:

- `lead` с типом `phone` или `phone-inline`;
- `phone-click` с теми же данными и UTM-атрибуцией.

После успешного сохранения формы должны появиться:

- `lead` с типом `request-submit`;
- `lead-notification` с фактическим состоянием уведомления.

Для проверки UTM откройте страницу с параметрами:

```text
/?utm_source=vk&utm_medium=social&utm_campaign=test-call
```

Затем нажмите телефон или отправьте тестовую заявку и проверьте `event.detail.attribution`.

## Как анализировать воронку

Смотреть нужно последовательность:

1. страница входа;
2. источник и кампания;
3. клик по телефону или открытие формы;
4. сохранение заявки `request-submit`;
5. состояние уведомления `lead-notification`;
6. при неподтверждённом уведомлении — возможный последующий клик по телефону.

Для рекламных каналов минимально нужны UTM:

```text
utm_source=vk
utm_medium=social
utm_campaign=parket_call
utm_content=post_01
```

Пример для расклейки или офлайн-материалов:

```text
utm_source=offline
utm_medium=qr
utm_campaign=leaflet_parquet
```

## Что нельзя делать

- Не удалять `parket36:lead` — на него завязана общая аналитика лидов.
- Не удалять `parket36:phone-click` — это отдельная звонковая цель.
- Не удалять `parket36:lead-notification` — иначе сохранение заявки снова будет смешано с доставкой уведомления.
- Не считать `request-submit` подтверждением, что Иван получил или прочитал сообщение.
- Не заменять технические названия целей русскими названиями.
- Не отправлять телефонные клики в Supabase как заявки: клик по телефону не равен заявке.
- Не добавлять сторонние счётчики без согласования, если они требуют cookies или меняют политику обработки данных.

## Следующие улучшения

1. Добавить реальный ID Метрики после его получения.
2. Завести цели в интерфейсе Метрики.
3. Сделать тестовый визит с UTM и проверить цели `phone-click`, `request-submit` и `lead-notification`.
4. После production-деплоя выполнить контролируемую заявку и проверить фактическое получение уведомления Иваном.
5. Через 1–2 недели после запуска трафика сравнить страницы по звонкам, сохранённым заявкам и неподтверждённым уведомлениям.
