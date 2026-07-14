# Обратная связь по доставке уведомления о заявке

После HTTP 200 заявка может быть успешно сохранена в `parket_leads`, но уведомление Ивану имеет отдельное состояние. Edge Function возвращает поле `notification`:

- `sent` — настроенный канал или каналы отработали успешно;
- `disabled` — Telegram и email не настроены;
- `partial_failure` — хотя бы один настроенный канал не подтвердил доставку;
- отсутствие поля или неизвестное значение — `unknown`, например при работе старой версии функции.

## Поведение формы

Факт сохранения заявки и подтверждение уведомления не смешиваются.

### `sent`

Посетитель видит обычное подтверждение отправки Ивану. Событие получает:

```text
notification: sent
notificationConfirmed: true
```

### `disabled`, `partial_failure`, `unknown`

Примеры неподтверждённой доставки:

```text
notification: disabled
notification: partial_failure
notification: unknown
notificationConfirmed: false
```

Посетитель видит, что заявка или номер сохранены, но автоматическое уведомление Ивану не подтверждено. Форма предлагает сразу позвонить по номеру `8 (900) 926-79-29`, чтобы клиент не ожидал обратного звонка вслепую.

Подробная форма дополнительно напоминает приложить фотографии к скопированному тексту.

Дубликат с `duplicate: true` не переписывается предупреждением: повторная отправка не создаёт новую запись, а существующее сообщение формы остаётся источником объяснения.

## Клиентский модуль

`js/lead-notification-feedback.js` подключается только на страницах с `#request-form` и строго после `js/main.js`.

Модуль:

1. оборачивает уже настроенный `window.fetch`, включая timeout и retry из `lead-reliability.js`;
2. читает клон успешного JSON-ответа Edge Function;
3. добавляет `notification`, `notificationConfirmed`, `duplicate` и `requestId` в событие `parket36:lead` типа `request-submit`;
4. при неподтверждённой доставке корректирует итоговый текст статуса;
5. создаёт отдельное событие `parket36:lead-notification`.

Payload заявки, схема Supabase и Edge Function не меняются.

## Аналитика

Браузерное событие:

```js
window.addEventListener('parket36:lead-notification', event => {
  console.log(event.detail);
});
```

Основные поля:

- `notification`;
- `notificationConfirmed`;
- `duplicate`;
- `requestId`;
- `formKind`: `assessment` или `callback`;
- `page`, `service`, `attribution`.

В `dataLayer` добавляется:

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

При подключённой Яндекс Метрике используется цель `lead-notification`.

`request-submit` остаётся событием успешного сохранения в Supabase. `lead-notification` позволяет отдельно оценить, было ли подтверждено автоматическое уведомление Ивану.

## Проверки

`tests/e2e/lead-notification-feedback.spec.mjs` проверяет:

1. `sent` сохраняет обычное подтверждение;
2. `disabled` сообщает о сохранённой заявке и рекомендует позвонить;
3. `partial_failure` не обещает обратный звонок;
4. ответ старой функции без `notification` считается `unknown`;
5. состояния попадают в браузерное событие и `dataLayer`.

`tools/check_lead_notification_feedback.py` защищает:

- разрешённый список состояний;
- отсутствие ложного подтверждения для `unknown`;
- текст звонкового fallback;
- подключение скрипта после `main.js`;
- соответствие backend-контракта, E2E и документации.

## Ограничение

Поле `sent` подтверждает результат вызова настроенного канала внутри Edge Function, но не гарантирует, что человек прочитал Telegram-сообщение или письмо. После первого production-деплоя всё равно нужна одна контролируемая заявка с фактической проверкой получения уведомления Иваном.
