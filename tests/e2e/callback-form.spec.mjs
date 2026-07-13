import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function allowClipboard(page) {
  await page.addInitScript(() => {
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

test('валидная callback-заявка сохраняет first-touch канал и специальное подтверждение', async ({ page }) => {
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
  await allowClipboard(page);

  await page.goto('/kontakty/?utm_source=yandex_business&utm_medium=local&utm_campaign=voronezh_parquet_launch&utm_content=business_profile');
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
});
