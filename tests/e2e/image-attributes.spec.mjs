import { test, expect } from '@playwright/test';

test('изображения портфолио имеют реальные размеры и безопасную загрузку', async ({ page }) => {
  await page.goto('/portfolio/');

  const images = page.locator('img[data-placeholder-image]');
  await expect(images).toHaveCount(6);

  for (let index = 0; index < 6; index += 1) {
    const image = images.nth(index);
    const state = await image.evaluate(element => ({
      src: element.getAttribute('src'),
      width: Number(element.getAttribute('width')),
      height: Number(element.getAttribute('height')),
      loading: element.getAttribute('loading'),
      decoding: element.getAttribute('decoding'),
      alt: element.getAttribute('alt'),
    }));

    const natural = await page.evaluate(async src => {
      const probe = new Image();
      probe.src = src;
      await probe.decode();
      return {
        width: probe.naturalWidth,
        height: probe.naturalHeight,
      };
    }, state.src);

    expect(natural.width).toBeGreaterThan(0);
    expect(natural.height).toBeGreaterThan(0);
    expect(state.width).toBe(natural.width);
    expect(state.height).toBe(natural.height);
    expect(state.loading).toBe('lazy');
    expect(state.decoding).toBe('async');
    expect(state.alt?.trim().length).toBeGreaterThan(0);
  }
});
