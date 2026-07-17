import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function prepareClipboard(page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

async function observeStatusHistory(page) {
  await page.evaluate(() => {
    const status = document.getElementById('request-status');
    window.__parketCallbackStatusHistory = [];
    if (!status || typeof MutationObserver !== 'function') return;

    const record = () => {
      const text = (status.textContent || '').trim();
      if (!text) return;
      const history = window.__parketCallbackStatusHistory;
      if (history.at(-1) !== text) history.push(text);
    };

    const observer = new MutationObserver(record);
    observer.observe(status, { childList: true, characterData: true, subtree: true });
    record();
  });
}

test('неподтверждённое callback-уведомление никогда не показывает ложное обещание звонка', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1101,
        notification: 'disabled'
      })
    });
  });
  await prepareClipboard(page);

  await page.goto('/kontakty/#callback');
  await observeStatusHistory(page);
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Алексей, +7 900 123-45-67');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Номер сохранён');
  await expect(status).toContainText('уведомление Ивану пока не настроено');
  await expect(status).toHaveAttribute('data-status-tone', 'warning');

  const history = await page.evaluate(() => window.__parketCallbackStatusHistory || []);
  expect(history).toContain('Отправляем заявку Ивану и готовим текст для копирования...');
  expect(history.some(text => text.includes('Он свяжется по указанному номеру'))).toBe(false);
  expect(history.some(text => text.includes('уведомление Ивану пока не настроено'))).toBe(true);
});

test('подтверждённое callback-уведомление сохраняет обычное обещание обратного звонка', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1102,
        notification: 'sent'
      })
    });
  });
  await prepareClipboard(page);

  await page.goto('/kontakty/#callback');
  await observeStatusHistory(page);
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 19:00');
  await page.locator('#request-contact').fill('Мария, +7 900 555-44-33');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  const status = page.locator('#request-status');
  await expect(status).toHaveText('Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.');
  await expect(status).toHaveAttribute('data-status-tone', 'success');

  const history = await page.evaluate(() => window.__parketCallbackStatusHistory || []);
  expect(history.some(text => text.includes('Он свяжется по указанному номеру'))).toBe(true);
});