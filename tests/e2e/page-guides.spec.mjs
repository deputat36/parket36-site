import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const servicePages = [
  '/uslugi/ciklevka-parketa/',
  '/uslugi/restavraciya-parketa/',
  '/uslugi/shlifovka-doshchatogo-pola/',
  '/uslugi/ukladka-parketa/',
  '/uslugi/pokrytie-lakom-i-maslom/',
  '/ceny/'
];

for (const path of servicePages) {
  test(`краткий ориентир ${path} помогает перейти к ответам без повторного приглашения`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    const guide = page.locator('[data-page-guide]');
    await expect(guide.locator('.service-brief dt')).toHaveCount(3);
    await expect(page.locator('.inline-lead')).toHaveCount(0);
    await expect(page.locator('.section--summary')).toHaveCount(0);
    const contents = guide.locator('details');
    await expect(contents).not.toHaveAttribute('open', '');
    await contents.locator('summary').click();
    const link = contents.getByRole('link').last();
    const href = await link.getAttribute('href');
    await link.click();
    const target = page.locator(href);
    await expect(target).toBeFocused();
    await expect(target).toBeInViewport({ ratio: 1 });
    await expect.poll(async () => {
      const top = await target.evaluate(node => node.getBoundingClientRect().top);
      const headerBottom = await page.locator('.topbar').evaluate(node => node.getBoundingClientRect().bottom);
      return top >= headerBottom && top < headerBottom + 180;
    }).toBeTruthy();
    const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(width.content).toBeLessThanOrEqual(width.viewport + 1);
  });
}

for (const width of [320, 1440]) {
  test(`статья ${width}px: содержание ведёт к разделу, доступность и прямой якорь сохраняются`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/sovety/pochemu-skripit-parket/');
    const nav = page.getByRole('navigation', { name: 'Разделы страницы' });
    await nav.locator('summary').click();
    const link = nav.getByRole('link', { name: 'Частые причины скрипа' });
    const href = await link.getAttribute('href');
    await link.click();
    await expect(page.locator(href)).toBeFocused();
    await page.reload();
    await expect(page.locator(href)).toBeInViewport({ ratio: 1 });
    await nav.locator('summary').click();
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(results.violations).toEqual([]);
    const widthResult = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(widthResult.content).toBeLessThanOrEqual(widthResult.viewport + 1);
    await page.locator('[data-page-guide]').scrollIntoViewIfNeeded();
    const screenshot = testInfo.outputPath(`contents-${width}.png`);
    await page.screenshot({ path: screenshot, animations: 'disabled' });
    await testInfo.attach('Содержание статьи', { path: screenshot, contentType: 'image/png' });
  });
}

test('содержание и краткий ориентир работают без JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto('/uslugi/ciklevka-parketa/');
  await expect(page.locator('.service-brief dt')).toHaveCount(3);
  const nav = page.getByRole('navigation', { name: 'Разделы страницы' });
  await nav.locator('summary').click();
  await nav.getByRole('link', { name: 'Состав работ', exact: true }).click();
  await expect(page.locator('h2:target')).toContainText('Что может входить в работу');
  await expect(page.locator('h2:target')).toBeInViewport({ ratio: 1 });
  await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
  await context.close();
});
