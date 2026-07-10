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

test('форма сохраняет статические landmark и skip-link без JavaScript', async ({ page }) => {
  await page.goto('/zayavka/');

  await expect(page.locator('a.skip-link[href="#main-content"]')).toHaveCount(1);
  await expect(page.locator('main#main-content')).toHaveCount(1);
  await expect(page.locator('#request-form')).toHaveCount(1);
  await expect(page.locator('link[data-css-bundle="true"]')).toHaveCount(1);
});
