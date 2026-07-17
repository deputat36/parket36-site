import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function prepareSignals(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__parketLead = null;
    window.__parketLeadNotification = null;
    window.__parketCallbackRequest = null;
    window.addEventListener('parket36:lead', event => {
      if (event.detail?.type === 'request-submit') window.__parketLead = event.detail;
    });
    window.addEventListener('parket36:lead-notification', event => {
      window.__parketLeadNotification = event.detail;
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

async function fillAssessment(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-task').fill('Нужно оценить состояние паркета и старого покрытия по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
}

async function fillCallback(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Мария, +7 900 555-44-33');
}

function mockSuccess(page, notification, leadId) {
  return page.route(leadEndpoint, async route => {
    const payload = route.request().postDataJSON();
    const body = {
      ok: true,
      request_id: payload.request_id,
      lead_id: leadId
    };
    if (notification !== undefined) body.notification = notification;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body)
    });
  });
}

function fallbackActions(page) {
  return page.locator('[data-lead-fallback-actions]');
}

test('sent подтверждает отправку Ивану и записывает состояние в аналитику', async ({ page }) => {
  await mockSuccess(page, 'sent', 901);
  await prepareSignals(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');
  await expect(fallbackActions(page)).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.__parketLead)).toMatchObject({
    type: 'request-submit',
    notification: 'sent',
    notificationConfirmed: true
  });
  await expect.poll(() => page.evaluate(() => window.__parketLeadNotification)).toMatchObject({
    notification: 'sent',
    notificationConfirmed: true,
    formKind: 'assessment'
  });
  const analytics = await page.evaluate(() => window.dataLayer.find(item => item.event === 'parket36_lead_notification'));
  expect(analytics).toMatchObject({ notification_state: 'sent', notification_confirmed: true });
});

test('disabled сообщает, что заявка сохранена, и показывает прямую кнопку звонка', async ({ page }) => {
  await mockSuccess(page, 'disabled', 902);
  await prepareSignals(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Заявка сохранена');
  await expect(status).toContainText('уведомление Ивану пока не настроено');
  await expect(status).toContainText('8 (900) 926-79-29');
  const actions = fallbackActions(page);
  await expect(actions).toBeVisible();
  await expect(actions.getByRole('link', { name: 'Позвонить Ивану' })).toHaveAttribute('href', 'tel:+79009267929');
  await expect.poll(() => page.evaluate(() => window.__parketLeadNotification)).toMatchObject({
    notification: 'disabled',
    notificationConfirmed: false,
    formKind: 'assessment'
  });
});

test('partial_failure в callback не обещает звонок и показывает два безопасных действия', async ({ page }) => {
  await mockSuccess(page, 'partial_failure', 903);
  await prepareSignals(page);
  await page.goto('/kontakty/#callback');
  await fillCallback(page);
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Номер сохранён');
  await expect(status).toContainText('доставку уведомления Ивану подтвердить не удалось');
  await expect(status).toContainText('8 (900) 926-79-29');
  const actions = fallbackActions(page);
  await expect(actions.getByRole('link', { name: 'Позвонить Ивану' })).toHaveAttribute('href', 'tel:+79009267929');
  await expect(actions.getByRole('link', { name: 'Открыть оценку по фото' })).toHaveAttribute('href', '/zayavka/');
  await expect.poll(() => page.evaluate(() => window.__parketCallbackRequest)).toMatchObject({
    type: 'callback-request',
    notification: 'partial_failure',
    notificationConfirmed: false
  });
  await expect.poll(() => page.evaluate(() => window.__parketLeadNotification)).toMatchObject({
    notification: 'partial_failure',
    formKind: 'callback'
  });
});

test('старый backend без notification считается unknown и не даёт ложного подтверждения', async ({ page }) => {
  await mockSuccess(page, undefined, 904);
  await prepareSignals(page);
  await page.goto('/kontakty/#callback');
  await fillCallback(page);
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  const status = page.locator('#request-status');
  await expect(status).toContainText('Номер сохранён');
  await expect(status).toContainText('уведомление Ивану не подтверждено');
  await expect(status).not.toContainText('Он свяжется по указанному номеру');
  await expect(fallbackActions(page).getByRole('link', { name: 'Позвонить Ивану' })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__parketLeadNotification)).toMatchObject({
    notification: 'unknown',
    notificationConfirmed: false,
    formKind: 'callback'
  });
});

test('ошибка backend сохраняет текстовый fallback и показывает кнопку звонка', async ({ page }) => {
  await page.route(leadEndpoint, route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'temporary_unavailable' })
  }));
  await prepareSignals(page);
  await page.goto('/zayavka/');
  await fillAssessment(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Автоматически отправить заявку не удалось');
  const actions = fallbackActions(page);
  await expect(actions).toBeVisible();
  await expect(actions.getByRole('link', { name: 'Позвонить Ивану' })).toHaveAttribute('href', 'tel:+79009267929');
  await expect(actions.getByRole('link', { name: 'Открыть оценку по фото' })).toHaveCount(0);
});
