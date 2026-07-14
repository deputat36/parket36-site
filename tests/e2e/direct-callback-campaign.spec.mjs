import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';
const callbackCampaignPath = '/kontakty/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=callback_post#callback';

test('прямая VK-ссылка открывает callback и сохраняет кампанию в заявке', async ({ page }) => {
  let payload;
  let submittedHeaders;

  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__directCallbackOpen = null;
    window.__directCallbackRequest = null;
    window.addEventListener('parket36:callback-open', event => {
      window.__directCallbackOpen = event.detail;
    });
    window.addEventListener('parket36:callback-request', event => {
      window.__directCallbackRequest = event.detail;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });

  await page.route(leadEndpoint, async route => {
    payload = route.request().postDataJSON();
    submittedHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: payload.request_id, lead_id: 806, notification: 'sent' })
    });
  });

  await page.goto(callbackCampaignPath);

  await expect(page).toHaveURL(/utm_content=callback_post#callback$/);
  await expect(page.locator('#callback')).toBeInViewport();
  await expect(page.locator('#request-form')).not.toHaveAttribute('data-callback-topic', /.+/);
  await expect.poll(() => page.evaluate(() => window.__directCallbackOpen)).toMatchObject({
    type: 'callback-open',
    trigger: 'hash-entry',
    topic: 'general',
    topicSource: 'general',
    attribution: {
      source: 'vk',
      medium: 'social',
      campaign: 'voronezh_parquet_launch',
      content: 'callback_post',
      landing: '/kontakty/'
    }
  });

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 19:00');
  await page.locator('#request-contact').fill('Ирина, +7 900 777-88-99');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка на обратный звонок отправлена');
  expect(payload).toMatchObject({
    service: 'Обратный звонок по паркетным работам',
    location: 'Воронеж',
    callback_time: 'После 19:00',
    contact: 'Ирина, +7 900 777-88-99',
    page: '/kontakty/',
    utm_source: 'vk',
    utm_medium: 'social',
    utm_campaign: 'voronezh_parquet_launch',
    utm_content: 'callback_post'
  });

  const referrer = new URL(submittedHeaders.referer);
  expect(referrer.pathname).toBe('/kontakty/');
  expect(referrer.search).toBe('');
  expect(referrer.hash).toBe('');

  await expect.poll(() => page.evaluate(() => window.__directCallbackRequest)).toMatchObject({
    type: 'callback-request',
    topic: 'general',
    topicSource: 'general',
    notification: 'sent',
    notificationConfirmed: true,
    attribution: { source: 'vk', content: 'callback_post', landing: '/kontakty/' }
  });

  const events = await page.evaluate(() => window.dataLayer.filter(item => item.event.startsWith('parket36_callback_')));
  expect(events).toHaveLength(2);
  expect(events[0]).toMatchObject({
    event: 'parket36_callback_open',
    trigger: 'hash-entry',
    callback_topic: 'general',
    attribution: { source: 'vk', content: 'callback_post' }
  });
  expect(events[1]).toMatchObject({
    event: 'parket36_callback_request',
    callback_topic: 'general',
    attribution: { source: 'vk', content: 'callback_post' }
  });
});
