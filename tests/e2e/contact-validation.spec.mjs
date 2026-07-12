import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

test('форма не отправляет заявку без пригодного номера для обратного звонка', async ({ page }) => {
  let attempts = 0;
  await page.route(leadEndpoint, async route => {
    attempts += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, lead_id: 999 })
    });
  });

  await page.goto('/zayavka/');
  await page.locator('#request-task').fill('Нужно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Иван, звонить по номеру 12345');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const contact = page.locator('#request-contact');
  await expect(page.locator('#request-status')).toContainText('не менее 10 цифр');
  await expect(contact).toHaveAttribute('aria-invalid', 'true');
  await expect(contact).toBeFocused();
  expect(attempts).toBe(0);
});

test('форма принимает распространённый формат российского телефона', async ({ page }) => {
  let submittedContact = '';
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    submittedContact = payload.contact;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: payload.request_id, lead_id: 1000 })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });

  await page.goto('/zayavka/');
  await page.locator('#request-task').fill('Нужно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Иван, +7 (900) 123-45-67');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');
  expect(submittedContact).toBe('Иван, +7 (900) 123-45-67');
});
