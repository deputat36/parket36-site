import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

async function fillMinimumRequest(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-task').fill('Нужно оценить старый паркет, щели и состояние покрытия по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
}

test('главная страница показывает основной оффер и рабочий телефон', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle(/Паркет36/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Циклёвка');

  const phone = page.locator('a[href="tel:+79009267929"]').first();
  await expect(phone).toBeVisible();
  await expect(phone).toHaveAttribute('href', 'tel:+79009267929');

  await page.evaluate(() => {
    window.__parketPhoneLead = null;
    window.addEventListener('parket36:phone-click', event => {
      window.__parketPhoneLead = event.detail;
    }, { once: true });
    document.querySelector('a[href^="tel:"]')?.addEventListener('click', event => {
      event.preventDefault();
    }, { once: true });
  });
  await phone.click();

  await expect.poll(() => page.evaluate(() => window.__parketPhoneLead?.href || '')).toBe('tel:+79009267929');
});

test('мобильное меню открывается и закрывается клавишей Escape', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  const toggle = page.locator('[data-menu-toggle]');
  const nav = page.locator('[data-nav]');

  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(nav).toHaveClass(/open/);

  await page.keyboard.press('Escape');
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(nav).not.toHaveClass(/open/);
});

test('шаблон формы заполняет задачу, а успешный backend сохраняет заявку', async ({ page }) => {
  let submittedPayload;
  await page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: submittedPayload.request_id, lead_id: 101, notification: 'sent' })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async text => {
          window.__parketCopiedText = text;
        }
      }
    });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Щели и дефекты' }).click();
  await expect(page.locator('#request-task')).toHaveValue(/щели/);

  await page.locator('#request-contact').fill('Иван, +7 900 000-00-00');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');
  expect(submittedPayload.task).toContain('щели');
  expect(submittedPayload.contact).toContain('+7 900 000-00-00');
  expect(submittedPayload.website).toBe('');
  expect(submittedPayload.company).toBe('');
  await expect.poll(() => page.evaluate(() => window.__parketCopiedText || '')).toContain('Здравствуйте, Иван!');
});

test('лимиты полей совпадают с backend и счётчик отражает длину задачи', async ({ page }) => {
  let submittedPayload;
  await page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: submittedPayload.request_id, lead_id: 303, notification: 'sent' })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });

  await page.goto('/zayavka/');

  const expectedLimits = {
    '#request-location': '160',
    '#request-area': '80',
    '#request-task': '3000',
    '#request-callback': '160',
    '#request-contact': '240'
  };
  for (const [selector, limit] of Object.entries(expectedLimits)) {
    await expect(page.locator(selector)).toHaveAttribute('maxlength', limit);
  }

  const task = page.locator('#request-task');
  const counter = page.locator('[data-lead-character-counter="request-task"]');
  await expect(task).toHaveAttribute('aria-describedby', /request-task-counter/);
  await expect(counter).toHaveText('0 / 3000');

  await task.click();
  await page.keyboard.insertText('а'.repeat(3005));
  expect((await task.inputValue()).length).toBe(3000);
  await expect(counter).toHaveText('3000 / 3000');

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');
  expect(submittedPayload.task.length).toBe(3000);
});

test('422 показывает конкретное поле без повторной отправки', async ({ page }) => {
  let attempts = 0;
  await page.route(leadEndpoint, async route => {
    attempts += 1;
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: false,
        error: 'field_too_long',
        request_id: payload.request_id,
        field: 'task',
        limit: 3000,
        received: 3001
      })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async text => {
          window.__parketCopiedText = text;
        }
      }
    });
  });

  await page.goto('/zayavka/');
  await fillMinimumRequest(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const task = page.locator('#request-task');
  const status = page.locator('#request-status');
  await expect(status).toContainText('Поле «Описание задачи» слишком длинное');
  await expect(status).toContainText('3000 символов');
  await expect(task).toHaveAttribute('aria-invalid', 'true');
  await expect(task).toBeFocused();
  await expect.poll(() => page.evaluate(() => window.__parketCopiedText || '')).toContain('Здравствуйте, Иван!');
  expect(attempts).toBe(1);
});

test('429 предлагает подождать без повторной отправки', async ({ page }) => {
  let attempts = 0;
  await page.route(leadEndpoint, async route => {
    attempts += 1;
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({ ok: false, error: 'rate_limited', request_id: payload.request_id })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async text => {
          window.__parketCopiedText = text;
        }
      }
    });
  });

  await page.goto('/zayavka/');
  await fillMinimumRequest(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  await expect(page.locator('#request-status')).toContainText('Подождите 15 минут');
  await expect.poll(() => page.evaluate(() => window.__parketCopiedText || '')).toContain('Здравствуйте, Иван!');
  expect(attempts).toBe(1);
});

test('форма сообщает об ошибках и блокирует повторную отправку', async ({ page }) => {
  let attempts = 0;
  let releaseResponse;
  const responseGate = new Promise(resolve => {
    releaseResponse = resolve;
  });

  await page.route(leadEndpoint, async route => {
    attempts += 1;
    const payload = route.request().postDataJSON();
    await responseGate;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: payload.request_id, lead_id: 202, notification: 'sent' })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });

  await page.goto('/');

  const form = page.locator('#request-form');
  const status = page.locator('#request-status');
  const task = page.locator('#request-task');

  await expect(status).toHaveAttribute('role', 'status');
  await expect(status).toHaveAttribute('aria-live', 'polite');
  await expect(status).toHaveAttribute('aria-atomic', 'true');
  await expect(form).toHaveAttribute('aria-busy', 'false');

  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();
  await expect(task).toHaveAttribute('aria-invalid', 'true');
  await expect(task).toBeFocused();
  await expect(status).toContainText('обязательное поле');

  await fillMinimumRequest(page);
  await expect(task).not.toHaveAttribute('aria-invalid');

  await page.evaluate(() => {
    const requestForm = document.getElementById('request-form');
    requestForm.requestSubmit();
    requestForm.dispatchEvent(new SubmitEvent('submit', { bubbles: true, cancelable: true }));
  });

  await expect.poll(() => attempts).toBe(1);
  await expect(form).toHaveAttribute('aria-busy', 'true');
  await expect(status).toContainText('уже отправляется');

  releaseResponse();
  await expect(status).toContainText('Заявка отправлена Ивану');
  await expect(form).toHaveAttribute('aria-busy', 'false');
  expect(attempts).toBe(1);
});

test('при отказе backend и clipboard форма показывает ручной fallback', async ({ page }) => {
  let attempts = 0;
  await page.route(leadEndpoint, async route => {
    attempts += 1;
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ ok: false, error: 'temporary_error' })
    });
  });

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async () => {
          throw new Error('clipboard_unavailable');
        }
      }
    });
  });

  await page.goto('/');
  await fillMinimumRequest(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();

  const fallback = page.locator('[data-request-fallback]');
  await expect(fallback).toBeVisible();
  await expect(fallback).toHaveValue(/Здравствуйте, Иван!/);
  await expect(fallback).toHaveValue(/Воронеж/);
  await expect(page.locator('#request-status')).toContainText('Скопируйте готовый текст ниже');
  expect(attempts).toBe(2);
});

test('страница 404 остаётся noindex и ведёт к заявке', async ({ page }) => {
  await page.goto('/404.html');

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Такой страницы нет');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
  await expect(page.getByRole('link', { name: 'Оценить по фото' }).first()).toHaveAttribute('href', '/zayavka/');
  await expect(page.getByRole('link', { name: 'На главную' })).toHaveAttribute('href', '/');
});
