import { test, expect } from '@playwright/test';

test('публичная сборка отдаёт растровую OG-карточку', async ({ page, request }) => {
  await page.goto('/');

  const imageUrl = await page.locator('meta[property="og:image"]').getAttribute('content');
  expect(imageUrl).toMatch(/^https:\/\/parket36\.ru\/img\/og\/og-[a-f0-9]{16}\.png$/);
  await expect(page.locator('meta[property="og:image:type"]')).toHaveAttribute('content', 'image/png');
  await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute('content', '1200');
  await expect(page.locator('meta[property="og:image:height"]')).toHaveAttribute('content', '630');
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary_large_image');
  await expect(page.locator('meta[name="twitter:image"]')).toHaveAttribute('content', imageUrl);

  const imagePath = new URL(imageUrl).pathname;
  const response = await request.get(imagePath);
  expect(response.ok()).toBeTruthy();
  expect(response.headers()['content-type']).toContain('image/png');
  const bytes = await response.body();
  expect(Array.from(bytes.subarray(0, 8))).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
});
