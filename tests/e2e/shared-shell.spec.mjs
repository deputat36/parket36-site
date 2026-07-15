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

test('главная и форма используют одинаковую полную общую оболочку', async ({ page }) => {
  const home = await readShell(page, '/');
  const request = await readShell(page, '/zayavka/');

  expect(request).toEqual(home);
  await expect(page.locator('a[href="tel:+79009267929"]').first()).toBeVisible();
  await expect(page.locator('section.final-cta a[href="#request"]')).toBeVisible();
});

test('верхнеуровневые страницы используют профильные header, footer и mobile CTA', async ({ page }) => {
  await page.goto('/');
  const canonicalFooter = await page.locator('footer.footer').evaluate(element => element.outerHTML);

  for (const profile of [
    { path: '/uslugi/', activeHref: '/uslugi/' },
    { path: '/ceny/', activeHref: '/ceny/' }
  ]) {
    await page.goto(profile.path);

    await expect(page.locator('header.topbar')).toHaveCount(1);
    await expect(page.locator('footer.footer')).toHaveCount(1);
    await expect(page.locator('div.mobile-cta')).toHaveCount(1);

    const activeLink = page.locator(`header.topbar nav a[href="${profile.activeHref}"]`);
    await expect(activeLink).toHaveClass(/active/);
    await expect(activeLink).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('header.topbar nav a[aria-current="page"]')).toHaveCount(1);

    const footer = await page.locator('footer.footer').evaluate(element => element.outerHTML);
    expect(footer).toBe(canonicalFooter);

    await expect(page.locator('div.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
    await expect(page.locator('div.mobile-cta a[href="/zayavka/"]')).toBeVisible();
    await expect(page.locator('div.mobile-cta a[href="#request"]')).toHaveCount(0);
  }
});
