import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function prepareBrowserSignals(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__parketCallbackOpen = null;
    window.__parketCallbackRequest = null;
    window.addEventListener('parket36:callback-open', event => {
      window.__parketCallbackOpen = event.detail;
    });
    window.addEventListener('parket36:callback-request', event => {
      window.__parketCallbackRequest = event.detail;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

test('короткая форма блокирует непригодный номер без запроса к backend', async ({ page }) => {
  let attempts = 0;
  await page.route(leadEndpoint, async route => {
    attempts += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/kontakty/');
  await page.getByRole('link', { name: 'Заказать обратный звонок' }).first().click();
  await expect(page.locator('#callback')).toBeInViewport();

  await page.locator('#request-contact').fill('Иван, 12345');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toContainText('не менее 10 цифр');
  await expect(page.locator('#request-contact')).toHaveAttribute('aria-invalid', 'true');
  expect(attempts).toBe(0);
});

test('валидная callback-заявка сохраняет first-touch канал и отдельные события', async ({ page }) => {
  let submittedPayload;
  let submittedHeaders;

  await page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    submittedHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: submittedPayload.request_id, lead_id: 801 })
    });
  });
  await prepareBrowserSignals(page);

  await page.goto('/kontakty/?utm_source=yandex_business&utm_medium=local&utm_campaign=voronezh_parquet_launch&utm_content=business_profile');
  await page.getByRole('link', { name: 'Заказать обратный звонок' }).first().click();
  await expect(page.locator('#callback')).toBeInViewport();

  await expect.poll(() => page.evaluate(() => window.__parketCallbackOpen)).toMatchObject({
    type: 'callback-open',
    href: '#callback',
    trigger: 'click',
    page: '/kontakty/',
    attribution: {
      source: 'yandex_business',
      medium: 'local',
      campaign: 'voronezh_parquet_launch',
      content: 'business_profile',
      landing: '/kontakty/'
    }
  });

  await page.locator('#request-location').fill('Воронеж, Северный район');
  await page.locator('#request-callback').fill('Сегодня после 18:00');
  await page.locator('#request-contact').fill('Алексей, +7 (900) 123-45-67');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toHaveText('Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.');
  await expect(page.getByRole('button', { name: 'Заказать обратный звонок' })).toBeEnabled();

  expect(submittedPayload).toMatchObject({
    service: 'Обратный звонок по паркетным работам',
    location: 'Воронеж, Северный район',
    task: 'Прошу перезвонить и проконсультировать по состоянию паркета или деревянного пола. Детали и фотографии сообщу после звонка.',
    callback_time: 'Сегодня после 18:00',
    contact: 'Алексей, +7 (900) 123-45-67',
    page: '/kontakty/',
    utm_source: 'yandex_business',
    utm_medium: 'local',
    utm_campaign: 'voronezh_parquet_launch',
    utm_content: 'business_profile'
  });

  const referrer = new URL(submittedHeaders.referer);
  expect(referrer.pathname).toBe('/kontakty/');
  expect(referrer.search).toBe('');

  await expect.poll(() => page.evaluate(() => window.__parketCallbackRequest)).toMatchObject({
    type: 'callback-request',
    service: 'Обратный звонок по паркетным работам',
    page: '/kontakty/',
    backend: 'supabase',
    attribution: {
      source: 'yandex_business',
      medium: 'local',
      campaign: 'voronezh_parquet_launch',
      content: 'business_profile',
      landing: '/kontakty/'
    }
  });

  const dataLayerEvents = await page.evaluate(() => window.dataLayer.filter(item => item.event.startsWith('parket36_callback_')));
  expect(dataLayerEvents).toHaveLength(2);
  expect(dataLayerEvents[0]).toMatchObject({
    event: 'parket36_callback_open',
    page: '/kontakty/',
    trigger: 'click',
    attribution: { source: 'yandex_business', medium: 'local' }
  });
  expect(dataLayerEvents[1]).toMatchObject({
    event: 'parket36_callback_request',
    page: '/kontakty/',
    service: 'Обратный звонок по паркетным работам',
    attribution: { source: 'yandex_business', medium: 'local' }
  });
});

test('переход со стоимости открывает callback один раз и сохраняет первую страницу', async ({ page }) => {
  let submittedPayload;
  let submittedHeaders;

  await page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    submittedHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: submittedPayload.request_id, lead_id: 802 })
    });
  });
  await prepareBrowserSignals(page);

  await page.goto('/ceny/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=price_post');
  await page.getByRole('link', { name: 'Заказать обратный звонок' }).click();

  await expect(page).toHaveURL(/\/kontakty\/#callback$/);
  await expect(page.locator('#callback')).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.__parketCallbackOpen)).toMatchObject({
    type: 'callback-open',
    href: '#callback',
    trigger: 'hash-entry',
    page: '/kontakty/',
    attribution: {
      source: 'vk',
      medium: 'social',
      campaign: 'voronezh_parquet_launch',
      content: 'price_post',
      landing: '/ceny/'
    }
  });

  const openEvents = await page.evaluate(() => window.dataLayer.filter(item => item.event === 'parket36_callback_open'));
  expect(openEvents).toHaveLength(1);
  expect(openEvents[0]).toMatchObject({
    event: 'parket36_callback_open',
    page: '/kontakty/',
    trigger: 'hash-entry',
    attribution: { source: 'vk', landing: '/ceny/' }
  });

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 19:00');
  await page.locator('#request-contact').fill('Мария, +7 900 555-44-33');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();
  await expect(page.locator('#request-status')).toContainText('Заявка на обратный звонок отправлена');

  expect(submittedPayload).toMatchObject({
    service: 'Обратный звонок по паркетным работам',
    page: '/kontakty/',
    utm_source: 'vk',
    utm_medium: 'social',
    utm_campaign: 'voronezh_parquet_launch',
    utm_content: 'price_post'
  });
  const firstTouchReferrer = new URL(submittedHeaders.referer);
  expect(firstTouchReferrer.pathname).toBe('/ceny/');
  expect(firstTouchReferrer.search).toBe('');
});
