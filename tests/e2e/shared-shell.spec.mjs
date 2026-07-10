import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

const selectors = [
  'header.topbar',
  'section.final-cta',
  'footer.footer',
  'div.mobile-cta'
];

async function readShell(page, path) {
  await page.goto(path);
  const shell = {};
  for (const selector of selectors) {
    const locator = page.locator(selector);
    await expect(locator).toHaveCount(1);
    shell[selector] = await locator.evaluate(element => element.outerHTML);
  }
  return shell;
}

test('главная и форма используют одинаковую общую оболочку', async ({ page }) => {
  const home = await readShell(page, '/');
  const request = await readShell(page, '/zayavka/');

  expect(request).toEqual(home);
  await expect(page.locator('a[href="tel:+79009267929"]').first()).toBeVisible();
  await expect(page.locator('a[href="#request"]').last()).toBeVisible();
});
