import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function installClipboard(page, mode = 'success') {
  await page.addInitScript(selectedMode => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async () => {
          if (selectedMode === 'failure') throw new Error('clipboard_unavailable');
        }
      }
    });
  }, mode);
}

async function observeStatusHistory(page) {
  await page.evaluate(() => {
    const status = document.querySelector('#request-status');
    window.__parketAssessmentStatusHistory = [];
    if (!status) return;

    const record = () => {
      const value = (status.textContent || '').trim();
      if (!value) return;
      const history = window.__parketAssessmentStatusHistory;
      if (history.at(-1) !== value) history.push(value);
    };

    new MutationObserver(record).observe(status, {
      childList: true,
      characterData: true,
      subtree: true
    });
    record();
  });
}

async function fillAssessment(page) {
  await page.locator('#request-task').fill('Нужно оценить старый паркет по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 (900) 123-45-67');
}

test('подробная форма не показывает ложный успех при отключённом уведомлении', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1201,
        notification: 'disabled'
      })
    });
  });
  await installClipboard(page, 'success');

  await page.goto('/zayavka/');
  await observeStatusHistory(page);
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('автоматическое уведомление Ивану пока не настроено');
  await expect(status).toHaveAttribute('data-status-tone', 'warning');

  const history = await page.evaluate(() => window.__parketAssessmentStatusHistory);
  expect(history.some(value => value.startsWith('Заявка отправлена Ивану'))).toBe(false);
  expect(history.some(value => value.startsWith('Заявка сохранена, но'))).toBe(true);
});

test('ручной текстовый fallback не показывает ложный успех при partial failure', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1202,
        notification: 'partial_failure'
      })
    });
  });
  await installClipboard(page, 'failure');

  await page.goto('/zayavka/');
  await observeStatusHistory(page);
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('доставку уведомления Ивану подтвердить не удалось');
  await expect(status).toContainText('Скопируйте готовый текст ниже');
  await expect(page.locator('[data-request-fallback]')).toBeVisible();
  await expect(status).toHaveAttribute('data-status-tone', 'warning');

  const history = await page.evaluate(() => window.__parketAssessmentStatusHistory);
  expect(history.some(value => value.startsWith('Заявка отправлена Ивану'))).toBe(false);
  expect(history.some(value => value.includes('Скопируйте готовый текст ниже'))).toBe(true);
});
