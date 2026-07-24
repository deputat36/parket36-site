import { expect, test } from '@playwright/test';

const abortMainScript = async page => {
  await page.route('**/js/main.*.js', route => route.abort());
};

test('подробная форма сохраняет введённые данные при неполной загрузке', async ({ page }) => {
  await abortMainScript(page);
  await page.goto('/zayavka/');

  const form = page.locator('#request-form');
  const submit = form.locator('[data-form-safety-submit="true"]');
  await expect(form).toHaveAttribute('data-form-safety', 'active');
  await expect(submit).toBeEnabled();

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('24 м²');
  await page.locator('#request-task').fill('Нужно оценить старый паркет со щелями и понять, можно ли восстановить покрытие без полной замены.');
  await page.locator('#request-contact').fill('Алексей, +7 900 111-22-33');

  const beforeUrl = page.url();
  await submit.click();

  await expect(page.locator('#request-status')).toContainText('Форма загрузилась не полностью');
  await expect(page.locator('#request-status')).toContainText('Данные не отправлены и остались в полях');
  await expect(page.locator('[data-form-safety-actions] a[href="tel:+79009267929"]')).toBeVisible();
  await expect(page.locator('#request-task')).toHaveValue(/старый паркет со щелями/);
  await expect(page.locator('#request-contact')).toHaveValue('Алексей, +7 900 111-22-33');
  expect(page.url()).toBe(beforeUrl);
  await expect(form).not.toHaveAttribute('aria-busy', 'true');
  await expect(submit).toBeEnabled();
});

test('callback-форма не перезагружает страницу без основного обработчика', async ({ page }) => {
  await abortMainScript(page);
  await page.goto('/kontakty/#callback');

  const form = page.locator('#request-form[data-form-kind="callback"]');
  const submit = form.locator('[data-form-safety-submit="true"]');
  await expect(form).toHaveAttribute('data-form-safety', 'active');

  await page.locator('#request-location').fill('Рамонь');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Ирина, +7 900 222-33-44');

  const beforeUrl = page.url();
  await submit.click();

  await expect(page.locator('#request-status')).toContainText('Форма загрузилась не полностью');
  await expect(page.locator('[data-form-safety-actions] a[href="tel:+79009267929"]')).toBeVisible();
  await expect(page.locator('[data-form-safety-actions] a[href="/zayavka/"]')).toBeVisible();
  await expect(page.locator('#request-contact')).toHaveValue('Ирина, +7 900 222-33-44');
  expect(page.url()).toBe(beforeUrl);
});
