import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function captureCallbackSignals(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__homeCallbackOpen = null;
    window.__homeCallbackRequest = null;
    window.addEventListener('parket36:callback-open', event => {
      window.__homeCallbackOpen = event.detail;
    });
    window.addEventListener('parket36:callback-request', event => {
      window.__homeCallbackRequest = event.detail;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

test('главная предлагает два статических пути к обратному звонку', async ({ page }) => {
  await page.goto('/');

  const links = page.locator('a[href="/kontakty/#callback"]');
  await expect(links).toHaveCount(2);
  await expect(links.nth(0)).toHaveText('Неудобно звонить — оставить номер для обратного звонка →');
  await expect(links.nth(1)).toHaveText('Удобнее, чтобы Иван позвонил сам — оставить номер →');

  await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toHaveText('Позвонить');
  await expect(page.locator('.mobile-cta a[href="#request"]')).toHaveText('Оценка по фото');
});

test('переход с главной сохраняет UTM и отправляет общую callback-заявку', async ({ page }) => {
  let payload;
  let submittedHeaders;

  await page.route(leadEndpoint, async route => {
    payload = route.request().postDataJSON();
    submittedHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: payload.request_id, lead_id: 804, notification: 'sent' })
    });
  });
  await captureCallbackSignals(page);

  await page.goto('/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=home_callback');
  await page.locator('a[href="/kontakty/#callback"]').first().click();

  await expect(page).toHaveURL(/\/kontakty\/#callback$/);
  await expect(page.locator('#callback')).toBeInViewport();
  await expect(page.locator('#request-form')).not.toHaveAttribute('data-callback-topic', /.+/);
  await expect.poll(() => page.evaluate(() => window.__homeCallbackOpen)).toMatchObject({
    type: 'callback-open',
    trigger: 'hash-entry',
    topic: 'general',
    topicSource: 'general',
    attribution: {
      source: 'vk',
      medium: 'social',
      campaign: 'voronezh_parquet_launch',
      content: 'home_callback',
      landing: '/'
    }
  });

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Ольга, +7 900 222-33-44');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка на обратный звонок отправлена');
  expect(payload).toMatchObject({
    service: 'Обратный звонок по паркетным работам',
    task: 'Прошу перезвонить и проконсультировать по состоянию паркета или деревянного пола. Детали и фотографии сообщу после звонка.',
    location: 'Воронеж',
    callback_time: 'После 18:00',
    contact: 'Ольга, +7 900 222-33-44',
    page: '/kontakty/',
    utm_source: 'vk',
    utm_medium: 'social',
    utm_campaign: 'voronezh_parquet_launch',
    utm_content: 'home_callback'
  });

  const referrer = new URL(submittedHeaders.referer);
  expect(referrer.pathname).toBe('/');
  expect(referrer.search).toBe('');

  await expect.poll(() => page.evaluate(() => window.__homeCallbackRequest)).toMatchObject({
    type: 'callback-request',
    topic: 'general',
    topicSource: 'general',
    notification: 'sent',
    notificationConfirmed: true,
    attribution: { source: 'vk', landing: '/' }
  });

  const callbackEvents = await page.evaluate(() => window.dataLayer.filter(item => item.event.startsWith('parket36_callback_')));
  expect(callbackEvents).toHaveLength(2);
  expect(callbackEvents[0]).toMatchObject({
    event: 'parket36_callback_open',
    callback_topic: 'general',
    callback_topic_source: 'general',
    attribution: { source: 'vk', landing: '/' }
  });
  expect(callbackEvents[1]).toMatchObject({
    event: 'parket36_callback_request',
    callback_topic: 'general',
    callback_topic_source: 'general',
    attribution: { source: 'vk', landing: '/' }
  });
});
