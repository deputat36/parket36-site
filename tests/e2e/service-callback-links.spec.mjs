import { expect, test } from '@playwright/test';

const servicePages = [
  ['/uslugi/ciklevka-parketa/', 'Циклёвка и шлифовка паркета в Воронеже'],
  ['/uslugi/restavraciya-parketa/', 'Реставрация и ремонт паркета в Воронеже']
];

async function prepareCallbackSignal(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__parketCallbackOpen = null;
    window.addEventListener('parket36:callback-open', event => {
      window.__parketCallbackOpen = event.detail;
    });
  });
}

for (const [path, heading] of servicePages) {
  test(`${path} содержит два статических пути к обратному звонку`, async ({ page }) => {
    await page.goto(path);

    await expect(page.getByRole('heading', { level: 1 })).toContainText(heading);
    const callbackLinks = page.locator('a[href="/kontakty/#callback"]');
    await expect(callbackLinks).toHaveCount(2);
    await expect(callbackLinks.nth(0)).toHaveText('Неудобно звонить — заказать обратный звонок →');
    await expect(callbackLinks.nth(1)).toHaveText('Оставить номер для обратного звонка →');
  });
}

test('переход с циклёвки сохраняет first-touch услугу и создаёт одно hash-entry событие', async ({ page }) => {
  await prepareCallbackSignal(page);

  await page.goto('/uslugi/ciklevka-parketa/?utm_source=avito&utm_medium=classified&utm_campaign=voronezh_parquet_launch&utm_content=service_listing_cyclevka');
  await page.locator('a[href="/kontakty/#callback"]').first().click();

  await expect(page).toHaveURL(/\/kontakty\/#callback$/);
  await expect(page.locator('#callback')).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.__parketCallbackOpen)).toMatchObject({
    type: 'callback-open',
    href: '#callback',
    trigger: 'hash-entry',
    page: '/kontakty/',
    attribution: {
      source: 'avito',
      medium: 'classified',
      campaign: 'voronezh_parquet_launch',
      content: 'service_listing_cyclevka',
      landing: '/uslugi/ciklevka-parketa/'
    }
  });

  const openEvents = await page.evaluate(() => window.dataLayer.filter(item => item.event === 'parket36_callback_open'));
  expect(openEvents).toHaveLength(1);
  expect(openEvents[0]).toMatchObject({
    event: 'parket36_callback_open',
    page: '/kontakty/',
    trigger: 'hash-entry',
    attribution: {
      source: 'avito',
      landing: '/uslugi/ciklevka-parketa/'
    }
  });
});
