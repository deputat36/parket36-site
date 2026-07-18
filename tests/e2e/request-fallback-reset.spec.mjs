import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function prepareClipboard(page) {
  await page.addInitScript(() => {
    window.__parketRejectClipboard = true;
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async () => {
          if (window.__parketRejectClipboard) throw new Error('clipboard_denied');
        }
      }
    });
  });
}

async function fillAssessment(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-task').fill('Нужно оценить старый паркет по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
}

async function mockSavedLead(page) {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 978,
        notification: 'disabled'
      })
    });
  });
}

test('успешное повторное копирование удаляет старый текстовый fallback', async ({ page }) => {
  await prepareClipboard(page);
  await mockSavedLead(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);

  const submit = page.getByRole('button', { name: 'Отправить заявку и скопировать текст' });
  const status = page.locator('#request-status');
  const fallback = page.locator('[data-request-fallback]');

  await submit.click();
  await expect(fallback).toBeVisible();
  await expect(fallback).toBeFocused();
  await expect(status).toContainText('Скопируйте готовый текст ниже');

  await page.evaluate(() => {
    window.__parketRejectClipboard = false;
  });
  await expect(submit).toBeEnabled();
  await submit.click();

  await expect(fallback).toHaveCount(0);
  await expect(status).toContainText('Текст скопирован');
  await expect(status).not.toContainText('Скопируйте готовый текст ниже');
  await expect(page.locator('[data-lead-fallback-actions]')).toBeVisible();
});
