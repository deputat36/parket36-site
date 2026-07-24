import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function mockLeadSuccess(page) {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 951,
        notification: 'sent'
      })
    });
  });
}

test('подробная форма показывает пять безопасных критериев готовности', async ({ page }) => {
  await page.goto('/zayavka/');

  const panel = page.locator('[data-request-readiness]');
  await expect(panel).toBeVisible();
  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('0 из 5');
  await expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  await expect(panel.locator('[data-readiness-key]')).toHaveCount(5);
  await expect(panel).toContainText('Форму можно отправить сейчас');
});

test('подробная форма становится готовой после заполнения полезных данных', async ({ page }) => {
  await page.goto('/zayavka/');

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-photos').selectOption({ label: 'Есть общий вид и дефекты крупно' });
  await page.locator('#request-task').fill('Нужно оценить старый паркет, щели и возможность циклёвки без полной замены пола.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');

  const panel = page.locator('[data-request-readiness]');
  await expect(panel).toHaveClass(/is-ready/);
  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('5 из 5');
  await expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '5');
  await expect(panel.locator('li.is-complete')).toHaveCount(5);
  await expect(panel).toContainText('Данных достаточно для первого ориентира');
});

test('короткая форма использует три критерия обратного звонка', async ({ page }) => {
  await page.goto('/kontakty/#callback');

  const panel = page.locator('[data-request-readiness]');
  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('0 из 3');

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Мария, +7 900 555-44-33');

  await expect(panel).toHaveClass(/is-ready/);
  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('3 из 3');
  await expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3');
  await expect(panel).toContainText('Данных достаточно, чтобы Иван мог перезвонить');
});

test('при отправке аналитика получает только счётчики и ключи, без значений полей', async ({ page }) => {
  await mockLeadSuccess(page);
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__requestReadiness = null;
    window.addEventListener('parket36:request-readiness', event => {
      window.__requestReadiness = event.detail;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });

  await page.goto('/zayavka/');
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-task').fill('Нужно оценить старый паркет, щели и возможность циклёвки без полной замены пола.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const detail = await page.evaluate(() => window.__requestReadiness);
  expect(detail).toMatchObject({
    type: 'request-readiness',
    formKind: 'assessment',
    completed: 4,
    total: 5,
    ready: false,
    missing: ['photos'],
    page: '/zayavka/'
  });
  expect(JSON.stringify(detail)).not.toContain('Воронеж');
  expect(JSON.stringify(detail)).not.toContain('Алексей');
  expect(JSON.stringify(detail)).not.toContain('9000000000');

  const analytics = await page.evaluate(() => window.dataLayer.find(item => item.event === 'parket36_request_readiness'));
  expect(analytics).toMatchObject({
    form_kind: 'assessment',
    completed_count: 4,
    total_count: 5,
    ready: false,
    missing_keys: ['photos'],
    page: '/zayavka/'
  });
});
