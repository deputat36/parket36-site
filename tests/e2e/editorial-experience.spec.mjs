import { expect, test } from '@playwright/test';

const pages = ['/', '/uslugi/ciklevka-parketa/', '/sovety/pochemu-skripit-parket/', '/kontakty/'];

for (const width of [1440, 390, 320]) {
  for (const path of pages) {
    test(`редизайн ${width}px ${path}: изображения, контакты и границы экрана`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      const brokenImages = [];
      page.on('response', response => {
        if (response.request().resourceType() === 'image' && !response.ok()) {
          brokenImages.push(response.url());
        }
      });
      await page.goto(path);
      await expect(page.locator('main h1')).toHaveCount(1);
      const heroImage = page.locator('main .hero__visual img, main .editorial-figure--hero img').first();
      await expect(heroImage).toBeVisible();
      await expect.poll(() => heroImage.evaluate(image => image.complete && image.naturalWidth > 0)).toBeTruthy();
      await expect(heroImage).not.toHaveAttribute('loading', 'lazy');
      await expect(page.locator('main [data-editorial-media] figcaption').first()).not.toBeEmpty();
      expect(brokenImages).toEqual([]);
      const bounds = await page.evaluate(() => ({ viewport: window.innerWidth, content: document.documentElement.scrollWidth }));
      expect(bounds.content).toBeLessThanOrEqual(bounds.viewport + 1);
      if (width < 1001) {
        await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
      } else {
        await expect(page.locator('header a.phone--header')).toBeVisible();
      }
      // These captures belong to this exact CI commit and are retained in the standard report artifact.
      const screenshot = testInfo.outputPath(`page-${width}.png`);
      await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
      await testInfo.attach('Страница целиком', { path: screenshot, contentType: 'image/png' });
    });
  }
}
