import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function prepareClipboard(page, { reject = false } = {}) {
  await page.addInitScript(({ shouldReject }) => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async () => {
          if (shouldReject) throw new Error('clipboard_denied');
        }
      }
    });
  }, { shouldReject: reject });
}

async function fillAssessment(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('20 м²');
  await page.locator('#request-task').fill('Нужно предварительно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
}

function mockSavedLead(page, notification) {
  return page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 951,
        notification
      })
    });
  });
}

test('неподтверждённое уведомление переводит фокус к аварийным действиям', async ({ page }) => {
  await prepareClipboard(page);
  await mockSavedLead(page, 'disabled');
  await page.goto('/zayavka/');
  await fillAssessment(page);

  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const actions = page.locator('[data-lead-fallback-actions]');
  await expect(actions).toBeVisible();
  await expect(actions).toBeFocused();
  await expect(actions).toHaveAttribute('tabindex', '-1');
  await expect(actions).toHaveAttribute('aria-describedby', 'request-status');
  await expect(page.locator('#request-status')).toContainText('уведомление Ивану пока не настроено');

  await page.keyboard.press('Tab');
  await expect(actions.getByRole('link', { name: 'Позвонить Ивану' })).toBeFocused();
});

test('на мобильном аварийные действия остаются выше фиксированной CTA-панели', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 780 });
  await prepareClipboard(page);
  await mockSavedLead(page, 'disabled');
  await page.goto('/zayavka/');
  await fillAssessment(page);

  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const actions = page.locator('[data-lead-fallback-actions]');
  const mobileCta = page.locator('.mobile-cta');
  await expect(actions).toBeFocused();
  await expect(mobileCta).toBeVisible();

  await expect.poll(async () => {
    const [actionsBox, ctaBox] = await Promise.all([
      actions.boundingBox(),
      mobileCta.boundingBox()
    ]);
    if (!actionsBox || !ctaBox) return false;
    return actionsBox.y + actionsBox.height <= ctaBox.y - 12;
  }).toBe(true);
});

test('ручной текстовый fallback сохраняет фокус при ошибке clipboard', async ({ page }) => {
  await prepareClipboard(page, { reject: true });
  await mockSavedLead(page, 'partial_failure');
  await page.goto('/zayavka/');
  await fillAssessment(page);

  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const fallback = page.locator('[data-request-fallback]');
  const actions = page.locator('[data-lead-fallback-actions]');
  await expect(fallback).toBeVisible();
  await expect(fallback).toBeFocused();
  await expect(actions).toBeVisible();
  await expect(actions).not.toBeFocused();
  await expect(page.locator('#request-status')).toContainText('Скопируйте готовый текст ниже');
});