import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const pages = [
  '/uslugi/ciklevka-parketa/', '/uslugi/restavraciya-parketa/',
  '/uslugi/shlifovka-doshchatogo-pola/', '/uslugi/ukladka-parketa/',
  '/uslugi/pokrytie-lakom-i-maslom/', '/uslugi/parket-i-poly/',
  '/kak-rabotaem/', '/sovety/parket-posle-vody/',
  '/sovety/shcheli-v-parkete/', '/sovety/pochemu-skripit-parket/',
  '/sovety/kak-sfotografirovat-pol-dlya-ocenki/'
];

for (const path of pages) {
  test(`пояснение соответствует странице и работает на телефоне: ${path}`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(path);
    const block = page.locator('[data-visual-explainer]');
    await expect(block).toHaveCount(1);
    await expect(block.locator('h2')).toHaveCount(1);
    await expect(block.locator('article')).toHaveCount(3);
    for (const card of await block.locator('article').all()) {
      await card.scrollIntoViewIfNeeded();
      const image = card.locator('img');
      await expect(image).toHaveAttribute('loading', 'lazy');
      await expect.poll(() => image.evaluate(i => i.complete && i.naturalWidth > 0)).toBeTruthy();
      await expect(card.locator('figcaption')).not.toBeEmpty();
      await expect(card.locator('h3')).not.toBeEmpty();
      expect(await card.locator('.visual-explainer__copy p').evaluate(p => parseFloat(getComputedStyle(p).fontSize))).toBeGreaterThanOrEqual(15);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
    await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
  });
}

test('вода и щели имеют разные иллюстрации, а памятка съёмки — три кадра', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('.quick-choice__grid a[href="/sovety/parket-posle-vody/"] img')).toHaveAttribute('src', /water-damage/);
  await expect(page.locator('.quick-choice__grid a[href="/sovety/shcheli-v-parkete/"] img')).toHaveAttribute('src', /parquet-gaps/);
  await expect(page.locator('.quick-choice__grid a[href="/sovety/pochemu-skripit-parket/"] img')).toHaveAttribute('src', /plank-movement/);
  await expect(page.locator('#request .photo-slot img')).toHaveCount(3);
  // Capture the updated page without sending the form or loading the live endpoint.
  await page.locator('img[loading="lazy"]').evaluateAll(async images => {
    await Promise.all(images.map(async image => { image.loading = 'eager'; await image.decode().catch(() => {}); }));
  });
  await page.screenshot({ path: testInfo.outputPath('home-390.png'), fullPage: true });
});

test('схемы, подписи и телефон доступны без JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 800 } });
  const page = await context.newPage();
  await page.goto('/sovety/parket-posle-vody/');
  const block = page.locator('[data-visual-explainer]');
  await expect(block.getByRole('heading', { name: 'Устранить источник влаги' })).toBeVisible();
  await expect(block).toContainText('Не шлифуйте деформированный влажный пол сразу');
  await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
  await context.close();
});

test('новое пояснение проходит axe и не содержит горизонтального переполнения на ПК', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/uslugi/ciklevka-parketa/');
  await page.locator('[data-visual-explainer]').scrollIntoViewIfNeeded();
  const results = await new AxeBuilder({ page }).include('[data-visual-explainer]').analyze();
  expect(results.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1441);
  await page.screenshot({ path: testInfo.outputPath('service-1440.png'), fullPage: true });
});
