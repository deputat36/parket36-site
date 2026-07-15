import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';
const PRIVATE = Object.freeze({
  contact: 'Клиент Privacy, +7 900 111-22-33',
  location: 'PRIVATE-LOCATION-улица-Тестовая-17',
  task: 'PRIVATE-TASK-проверить-дефект-у-двери',
  callback: 'PRIVATE-CALLBACK-сегодня-после-19-00'
});

async function prepareAnalyticsCapture(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__parketAnalyticsSignals = [];
    window.parket36MetrikaId = 12345678;
    window.ym = (...args) => {
      window.__parketAnalyticsSignals.push({ channel: 'metrika', args });
    };

    const capture = name => {
      window.addEventListener(name, event => {
        window.__parketAnalyticsSignals.push({
          channel: 'custom-event',
          name,
          detail: JSON.parse(JSON.stringify(event.detail || {}))
        });
      });
    };

    [
      'parket36:lead',
      'parket36:phone-click',
      'parket36:lead-notification',
      'parket36:callback-open',
      'parket36:callback-request'
    ].forEach(capture);

    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

function mockSuccessfulLead(page, leadId) {
  let submittedPayload;
  const routePromise = page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: submittedPayload.request_id,
        lead_id: leadId,
        notification: 'sent'
      })
    });
  });
  return { routePromise, getPayload: () => submittedPayload };
}

async function readAnalytics(page) {
  return page.evaluate(() => ({
    customAndMetrika: window.__parketAnalyticsSignals || [],
    dataLayer: window.dataLayer || []
  }));
}

function expectNoPrivateData(analytics) {
  const serialized = JSON.stringify(analytics);
  for (const value of Object.values(PRIVATE)) {
    expect(serialized).not.toContain(value);
  }
  expect(serialized).not.toContain('9001112233');
  expect(serialized).not.toContain('+79001112233');
}

test('полная заявка не передаёт контакт и свободный текст в аналитику', async ({ page }) => {
  const lead = mockSuccessfulLead(page, 1101);
  await lead.routePromise;
  await prepareAnalyticsCapture(page);

  await page.goto('/zayavka/?utm_source=privacy-test&utm_medium=e2e&utm_campaign=analytics-contract');
  await page.locator('#request-location').fill(PRIVATE.location);
  await page.locator('#request-area').fill('24 м²');
  await page.locator('#request-task').fill(PRIVATE.task);
  await page.locator('#request-callback').fill(PRIVATE.callback);
  await page.locator('#request-contact').fill(PRIVATE.contact);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');
  await expect.poll(async () => {
    const analytics = await readAnalytics(page);
    return analytics.customAndMetrika.some(item => (
      item.channel === 'custom-event' && item.name === 'parket36:lead-notification'
    ));
  }).toBe(true);

  expect(lead.getPayload()).toMatchObject({
    contact: PRIVATE.contact,
    location: PRIVATE.location,
    task: PRIVATE.task,
    callback_time: PRIVATE.callback
  });

  const analytics = await readAnalytics(page);
  expectNoPrivateData(analytics);
  expect(analytics.customAndMetrika).toEqual(expect.arrayContaining([
    expect.objectContaining({
      channel: 'custom-event',
      name: 'parket36:lead',
      detail: expect.objectContaining({
        type: 'request-submit',
        page: '/zayavka/',
        service: expect.any(String),
        backend: 'supabase'
      })
    }),
    expect.objectContaining({
      channel: 'custom-event',
      name: 'parket36:lead-notification',
      detail: expect.objectContaining({
        notification: 'sent',
        notificationConfirmed: true,
        formKind: 'assessment'
      })
    })
  ]));
  expect(analytics.dataLayer).toEqual(expect.arrayContaining([
    expect.objectContaining({
      event: 'parket36_lead_notification',
      notification_state: 'sent',
      form_kind: 'assessment'
    })
  ]));
});

test('callback-заявка не передаёт контакт, адрес и время связи в аналитику', async ({ page }) => {
  const lead = mockSuccessfulLead(page, 1102);
  await lead.routePromise;
  await prepareAnalyticsCapture(page);

  await page.goto('/kontakty/?utm_source=privacy-test&utm_medium=e2e&utm_campaign=callback-contract#callback');
  await page.locator('#request-location').fill(PRIVATE.location);
  await page.locator('#request-task').fill(PRIVATE.task);
  await page.locator('#request-callback').fill(PRIVATE.callback);
  await page.locator('#request-contact').fill(PRIVATE.contact);
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка на обратный звонок отправлена Ивану');
  await expect.poll(async () => {
    const analytics = await readAnalytics(page);
    return analytics.customAndMetrika.some(item => (
      item.channel === 'custom-event' && item.name === 'parket36:callback-request'
    ));
  }).toBe(true);

  expect(lead.getPayload()).toMatchObject({
    contact: PRIVATE.contact,
    location: PRIVATE.location,
    task: PRIVATE.task,
    callback_time: PRIVATE.callback
  });

  const analytics = await readAnalytics(page);
  expectNoPrivateData(analytics);
  expect(analytics.customAndMetrika).toEqual(expect.arrayContaining([
    expect.objectContaining({
      channel: 'custom-event',
      name: 'parket36:callback-request',
      detail: expect.objectContaining({
        type: 'callback-request',
        page: '/kontakty/',
        notification: 'sent',
        notificationConfirmed: true
      })
    })
  ]));
  expect(analytics.dataLayer).toEqual(expect.arrayContaining([
    expect.objectContaining({
      event: 'parket36_callback_request',
      page: '/kontakty/',
      notification_state: 'sent'
    })
  ]));
});
