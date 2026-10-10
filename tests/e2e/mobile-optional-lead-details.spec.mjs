import { expect, test } from '@playwright/test';

const endpoint = '**/functions/v1/parket-public-lead';

test('на телефоне подробная заявка показывает обязательные поля и раскрывает уточнения', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/zayavka/');

  const details = page.locator('#request-form .request-form__details');
  const toggle = details.locator('summary');

  await expect(details).not.toHaveAttribute('open', '');
  await expect(toggle).toBeVisible();
  await expect(page.locator('#request-task')).toBeVisible();
  await expect(page.locator('#request-contact')).toBeVisible();
  await expect(page.locator('#request-location')).toBeHidden();
  await expect(page.getByRole('button', { name: 'Отправить заявку и скопировать текст' })).toBeVisible();

  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(details).toHaveAttribute('open', '');
  await expect(page.locator('#request-location')).toBeVisible();
  await page.locator('#request-location').fill('Воронеж');

  await toggle.click();
  await expect(details).not.toHaveAttribute('open', '');
  await expect(page.locator('#request-location')).toBeHidden();
  await expect(page.locator('#request-location')).toHaveValue('Воронеж');
});

test('мобильный обратный звонок отправляется без необязательных полей', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let payload = null;
  await page.route(endpoint, async route => {
    payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1351,
        notification: 'sent'
      })
    });
  });
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
  await page.goto('/kontakty/#callback');
  const details = page.locator('#request-form .request-form__details');

  await expect(details).not.toHaveAttribute('open', '');
  await expect(page.locator('#request-location')).toBeHidden();
  await page.locator('#request-contact').fill('Иван, +7 900 123-45-67');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка на обратный звонок отправлена Ивану');
  expect(payload).toMatchObject({
    contact: 'Иван, +7 900 123-45-67',
    page: '/kontakty/',
    service: 'Обратный звонок по паркетным работам'
  });
  await expect(details).not.toHaveAttribute('open', '');
});

test('на широком экране уточнения открыты сразу в обеих формах', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/zayavka/');
  await expect(page.locator('#request-form .request-form__details')).toHaveAttribute('open', '');
  await expect(page.locator('#request-area')).toBeVisible();
  await page.goto('/kontakty/');
  await expect(page.locator('#request-form .request-form__details')).toHaveAttribute('open', '');
  await expect(page.locator('#request-callback')).toBeVisible();
});
