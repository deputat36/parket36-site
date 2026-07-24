import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

test('обязательная навигация доступна без JavaScript', async ({ page }) => {
  await page.goto('/');

  const skipLink = page.locator('a.skip-link[href="#main-content"]');
  await expect(skipLink).toHaveCount(1);
  await expect(page.locator('main#main-content')).toHaveCount(1);

  const menuToggle = page.locator('[data-menu-toggle]');
  await expect(menuToggle).toHaveAttribute('aria-controls', 'site-navigation');
  await expect(menuToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('nav#site-navigation[data-nav]')).toHaveCount(1);

  await expect(page.locator('a[href="tel:+79009267929"]').first()).toBeVisible();
  await expect(page.locator('link[data-css-bundle="true"]')).toHaveCount(1);
});

test('подробная форма без JavaScript не имитирует отправку и не стирает поля', async ({ page }) => {
  await page.goto('/zayavka/');

  const form = page.locator('#request-form');
  const submit = form.locator('[data-form-safety-submit="true"]');
  await expect(page.locator('a.skip-link[href="#main-content"]')).toHaveCount(1);
  await expect(page.locator('main#main-content')).toHaveCount(1);
  await expect(form).toHaveAttribute('data-form-safety', 'pending');
  await expect(submit).toBeDisabled();
  await expect(form.locator('[data-form-no-script="true"]')).toBeVisible();
  await expect(form.locator('[data-form-no-script="true"] a[href="tel:+79009267929"]')).toBeVisible();

  await page.locator('#request-task').fill('Описание пола остаётся в форме');
  await page.locator('#request-contact').fill('Алексей, +7 900 111-22-33');
  const beforeUrl = page.url();
  await page.locator('#request-contact').press('Enter');
  await page.waitForTimeout(150);

  expect(page.url()).toBe(beforeUrl);
  await expect(page.locator('#request-task')).toHaveValue('Описание пола остаётся в форме');
  await expect(page.locator('#request-contact')).toHaveValue('Алексей, +7 900 111-22-33');
  await expect(page.locator('link[data-css-bundle="true"]')).toHaveCount(1);
});

test('callback-форма без JavaScript оставляет только безопасный звонок', async ({ page }) => {
  await page.goto('/kontakty/#callback');

  const form = page.locator('#request-form[data-form-kind="callback"]');
  await expect(form).toHaveAttribute('data-form-safety', 'pending');
  await expect(form.locator('[data-form-safety-submit="true"]')).toBeDisabled();
  await expect(form.locator('[data-form-no-script="true"]')).toContainText('данные не отправлены');
  await expect(form.locator('[data-form-no-script="true"] a[href="tel:+79009267929"]')).toBeVisible();
});
