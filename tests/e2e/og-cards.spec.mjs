import { test, expect } from '@playwright/test';

function schemaNodes(blocks) {
  const nodes = [];
  for (const block of blocks) {
    const payload = JSON.parse(block);
    if (Array.isArray(payload)) {
      nodes.push(...payload);
    } else if (Array.isArray(payload['@graph'])) {
      nodes.push(...payload['@graph']);
    } else {
      nodes.push(payload);
    }
  }
  return nodes;
}

async function ogImage(page) {
  return page.locator('meta[property="og:image"]').getAttribute('content');
}

async function structuredImage(page, type) {
  const blocks = await page.locator('script[type="application/ld+json"]').allTextContents();
  const node = schemaNodes(blocks).find(item => {
    const value = item['@type'];
    return value === type || (Array.isArray(value) && value.includes(type));
  });
  return node?.image;
}

test('публичная сборка отдаёт единый растровый OG и JSON-LD image', async ({ page, request }) => {
  await page.goto('/');

  const imageUrl = await ogImage(page);
  expect(imageUrl).toMatch(/^https:\/\/parket36\.ru\/img\/og\/og-[a-f0-9]{16}\.png$/);
  await expect(page.locator('meta[property="og:image:type"]')).toHaveAttribute('content', 'image/png');
  await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute('content', '1200');
  await expect(page.locator('meta[property="og:image:height"]')).toHaveAttribute('content', '630');
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary_large_image');
  await expect(page.locator('meta[name="twitter:image"]')).toHaveAttribute('content', imageUrl);
  expect(await structuredImage(page, 'ProfessionalService')).toBe(imageUrl);

  const imagePath = new URL(imageUrl).pathname;
  const response = await request.get(imagePath);
  expect(response.ok()).toBeTruthy();
  expect(response.headers()['content-type']).toContain('image/png');
  const bytes = await response.body();
  expect(Array.from(bytes.subarray(0, 8))).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);

  await page.goto('/sovety/kak-proverit-shlifovku-parketa-pered-lakom/');
  const articleImage = await ogImage(page);
  expect(articleImage).toMatch(/^https:\/\/parket36\.ru\/img\/og\/og-[a-f0-9]{16}\.png$/);
  expect(await structuredImage(page, 'Article')).toBe(articleImage);
}