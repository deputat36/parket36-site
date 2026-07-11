import { test, expect } from '@playwright/test';

test('изображения портфолио имеют реальные размеры и безопасную загрузку', async ({ page }) => {
  await page.goto('/portfolio/');

  const images = page.locator('img[data-placeholder-image]');
  await expect(images).toHaveCount(6);

  for (let index = 0; index < 6; index += 1) {
    const image = images.nth(index);
    await image.scrollIntoViewIfNeeded();
    await expect(image).toBeVisible();
    await expect.poll(async () => image.evaluate(element => (
      element.complete && element.naturalWidth > 0 && element.naturalHeight > 0
    ))).toBe(true);

    const state = await image.evaluate(element => ({
      width: Number(element.getAttribute('width')),
      height: Number(element.getAttribute('height')),
      naturalWidth: element.naturalWidth,
      naturalHeight: element.naturalHeight,
      loading: element.getAttribute('loading'),
      decoding: element.getAttribute('decoding'),
      alt: element.getAttribute('alt'),
    }));

    expect(state.width).toBe(state.naturalWidth);
    expect(state.height).toBe(state.naturalHeight);
    expect(state.loading).toBe('lazy');
    expect(state.decoding).toBe('async');
    expect(state.alt?.trim().length).toBeGreaterThan(0);
  }
});
