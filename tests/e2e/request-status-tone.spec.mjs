import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function mockClipboard(page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

async function fillAssessment(page) {
  await page.locator('#request-task').fill('Нужно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Иван, +7 (900) 123-45-67');
}

test('шаблон задачи показывает нейтральный информационный статус', async ({ page }) => {
  await page.goto('/zayavka/');
  await page.getByRole('button', { name: 'Циклёвка' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Шаблон добавлен');
  await expect(status).toHaveAttribute('data-status-tone', 'info');
  await expect(status).toHaveAttribute('role', 'status');
  await expect(status).toHaveAttribute('aria-live', 'polite');
  await expect(status).toHaveAttribute('aria-atomic', 'true');
});

test('ошибка телефона получает красный error-статус', async ({ page }) => {
  await page.goto('/zayavka/');
  await page.locator('#request-task').fill('Нужно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Иван, 12345');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('не менее 10 цифр');
  await expect(status).toHaveAttribute('data-status-tone', 'error');
});

test('подтверждённое уведомление получает зелёный success-статус', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1201,
        notification: 'sent'
      })
    });
  });
  await mockClipboard(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Заявка отправлена Ивану');
  await expect(status).toHaveAttribute('data-status-tone', 'success');
});

test('неподтверждённое уведомление получает warning-статус', async ({ page }) => {
  await page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        request_id: payload.request_id,
        lead_id: 1202,
        notification: 'disabled'
      })
    });
  });
  await mockClipboard(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('уведомление Ивану пока не настроено');
  await expect(status).toHaveAttribute('data-status-tone', 'warning');
});

test('ошибка backend получает error-статус и сохраняет fallback', async ({ page }) => {
  await page.route(leadEndpoint, route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'temporary_unavailable' })
  }));
  await mockClipboard(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Автоматически отправить заявку не удалось');
  await expect(status).toHaveAttribute('data-status-tone', 'error');
  await expect(page.locator('[data-lead-fallback-actions]')).toBeVisible();
});
