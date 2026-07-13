import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';
const campaignConfig = JSON.parse(
  readFileSync(new URL('../../data/campaign-links.json', import.meta.url), 'utf8')
);

function campaignEntry(name) {
  const entry = campaignConfig.links.find(item => item.name === name);
  if (!entry) throw new Error(`Campaign entry is missing: ${name}`);
  return entry;
}

function trackedPath(entry) {
  const params = new URLSearchParams({
    utm_source: entry.source,
    utm_medium: entry.medium,
    utm_campaign: campaignConfig.campaign,
    utm_content: entry.content
  });
  if (entry.term) params.set('utm_term', entry.term);
  return `${entry.path}?${params}`;
}

async function allowClipboard(page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async text => {
          window.__parketCopiedText = text;
        }
      }
    });
  });
}

async function fillMinimumRequest(page) {
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-task').fill('Нужно оценить состояние старого паркета по фотографиям.');
  await page.locator('#request-contact').fill('Алексей, +7 900 000-00-00');
}

test('UTM сохраняются после навигации, а первая посадочная передаётся в referrer заявки', async ({ page }) => {
  const entry = campaignEntry('VK — главная страница');
  let submittedPayload;
  let submittedHeaders;

  await page.route(leadEndpoint, async route => {
    submittedPayload = route.request().postDataJSON();
    submittedHeaders = route.request().headers();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: submittedPayload.request_id, lead_id: 701 })
    });
  });
  await allowClipboard(page);

  await page.goto(trackedPath(entry));
  await expect.poll(() => page.evaluate(() => window.parket36Attribution)).toMatchObject({
    source: 'vk',
    medium: 'social',
    campaign: 'voronezh_parquet_launch',
    content: 'organic_post_home',
    landing: '/'
  });

  await page.getByRole('link', { name: /Работы в Воронеже и области/ }).click();
  await expect(page).toHaveURL(/\/kontakty\/$/);
  await page.getByRole('link', { name: 'Получить оценку по фото' }).first().click();
  await expect(page).toHaveURL(/\/zayavka\/$/);

  await fillMinimumRequest(page);
  await page.getByRole('button', { name: 'Отправить заявку и скопировать текст' }).click();
  await expect(page.locator('#request-status')).toContainText('Заявка отправлена Ивану');

  expect(submittedPayload).toMatchObject({
    page: '/zayavka/',
    utm_source: 'vk',
    utm_medium: 'social',
    utm_campaign: 'voronezh_parquet_launch',
    utm_content: 'organic_post_home',
    utm_term: ''
  });

  const firstTouchReferrer = new URL(submittedHeaders.referer);
  expect(firstTouchReferrer.pathname).toBe('/');
  expect(firstTouchReferrer.search).toBe('');
  expect(firstTouchReferrer.hash).toBe('');
  await expect.poll(() => page.evaluate(() => window.__parketCopiedText || '')).toContain('Страница входа: /');
});

test('первая кампания не перезаписывается следующим UTM-переходом в той же сессии', async ({ page }) => {
  const firstEntry = campaignEntry('VK — главная страница');
  const secondEntry = campaignEntry('Авито — циклёвка паркета');

  await page.goto(trackedPath(firstEntry));
  await page.goto(trackedPath(secondEntry));

  await expect.poll(() => page.evaluate(() => window.parket36Attribution)).toMatchObject({
    source: 'vk',
    medium: 'social',
    campaign: 'voronezh_parquet_launch',
    content: 'organic_post_home',
    landing: '/'
  });

  await page.evaluate(() => {
    window.__parketPhoneLead = null;
    window.addEventListener('parket36:phone-click', event => {
      window.__parketPhoneLead = event.detail;
    }, { once: true });
    document.querySelector('a[href^="tel:"]')?.addEventListener('click', event => {
      event.preventDefault();
    }, { once: true });
  });
  await page.locator('a[href^="tel:"]').first().click();

  await expect.poll(() => page.evaluate(() => window.__parketPhoneLead?.attribution)).toMatchObject({
    source: 'vk',
    medium: 'social',
    content: 'organic_post_home',
    landing: '/'
  });
});
