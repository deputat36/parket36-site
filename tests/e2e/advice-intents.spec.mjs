import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const drying = [
  'skolko-sohnet-lak-na-parkete',
  'kogda-mozhno-hodit-po-parketu-posle-lakirovki',
  'kogda-mozhno-stavit-mebel-posle-lakirovki-parketa',
  'kogda-mozhno-stelit-kover-posle-lakirovki-parketa',
  'kogda-mozhno-myt-parket-posle-lakirovki'
];
const peeling = ['lak-na-parkete-otslaivaetsya', 'pochemu-lak-na-parkete-shelushitsya-posle-lakirovki'];

for (const group of [drying, peeling]) {
  for (const [index, slug] of group.entries()) {
    test(`связанные ответы и FAQ согласованы: ${slug}`, async ({ page }) => {
      await page.goto(`/sovety/${slug}/`);
      const heading = await page.locator('h1').innerText();
      const nav = page.locator('.advice-route');
      await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
      await expect(nav.getByRole('link')).toHaveCount(group.length - 1);
      const faq = await page.locator('.faq details').evaluateAll(nodes => nodes.map(node => ({
        question: node.querySelector('summary').textContent.trim(),
        answer: node.querySelector('p').textContent.trim()
      })));
      const structured = await page.locator('script[type="application/ld+json"]').evaluateAll(nodes => nodes
        .flatMap(node => { const data = JSON.parse(node.textContent); return data['@graph'] || [data]; }));
      expect(structured.find(node => node['@type'] === 'Article').headline).toBe(heading);
      expect(structured.find(node => node['@type'] === 'FAQPage').mainEntity.map(node => ({
        question: node.name, answer: node.acceptedAnswer.text
      }))).toEqual(faq);
      const next = group[(index + 1) % group.length];
      await nav.locator(`a[href="/sovety/${next}/"]`).click();
      await expect(page).toHaveURL(new RegExp(`/sovety/${next}/$`));
      await expect(page.locator('h1')).not.toHaveText(heading);
      await expect(page.locator('.advice-route [aria-current="page"]')).toHaveCount(1);
    });
  }
}

for (const width of [320, 1440]) {
  test(`таблица и переходы между ответами доступны при ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/sovety/${drying[0]}/`);
    const table = page.getByRole('table', { name: 'Разные действия — разные условия допуска' });
    await table.scrollIntoViewIfNeeded();
    await expect(table.getByRole('rowheader')).toHaveCount(5);
    const dimensions = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(results.violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`drying-table-${width}.png`), animations: 'disabled' });
    await page.goto(`/sovety/${peeling[1]}/`);
    await expect(page.locator('.article-answer')).toBeVisible();
    const peelingResults = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(peelingResults.violations).toEqual([]);
  });
}

test('путь от первой ходьбы до уборки работает без JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 900 } });
  const page = await context.newPage();
  await page.goto(`/sovety/${drying[0]}/`);
  for (const slug of drying.slice(1)) {
    await page.locator(`.advice-route a[href="/sovety/${slug}/"]`).click();
    await expect(page.locator('.article-answer')).toBeVisible();
    await expect(page.locator('.article-answer')).not.toHaveText('');
  }
  await page.locator('[data-page-guide] summary').click();
  await page.locator('[data-page-guide] a').first().click();
  await expect(page.locator('h2:target')).toBeInViewport({ ratio: 1 });
  await expect(page.locator('h2:target')).toBeFocused();
  await expect(page.locator('.final-cta a[href="tel:+79009267929"]')).toHaveCount(1);
  await context.close();
});

for (const height of [700, 900]) {
  test(`нижняя панель не перекрывает содержание после нативной прокрутки: ${height}px`, async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height } });
    const page = await context.newPage();
    await page.goto(`/sovety/${drying[4]}/`);
    const summary = page.locator('[data-page-guide] summary');
    // Native end alignment reproduces the position at which a fixed panel used
    // to cover an otherwise visible control. The click remains an ordinary click.
    await summary.evaluate(node => node.scrollIntoView({ block: 'end', behavior: 'instant' }));
    const clearance = await summary.evaluate(node => {
      const panel = document.querySelector('.mobile-cta').getBoundingClientRect();
      return panel.top - node.getBoundingClientRect().bottom;
    });
    expect(clearance).toBeGreaterThanOrEqual(0);
    await summary.click();
    await expect(page.locator('[data-page-guide] details')).toHaveAttribute('open', '');
    await page.locator('[data-page-guide] a').first().click();
    await expect(page.locator('h2:target')).toBeInViewport({ ratio: 1 });
    await context.close();
  });
}
