import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const searchName = 'Найдите совет по вашей проблеме';
const visibleCards = page => page.locator('#advice-catalog .service-card:not([hidden])');

for (const [query, href] of [
  ['У меня пол скрипит', '/sovety/pochemu-skripit-parket/'],
  ['затопили паркет', '/sovety/parket-posle-vody/'],
  ['ПОТЁРТОСТИ!!!', '/sovety/staryy-lak-na-parkete/']
]) {
  test(`поиск находит подходящий материал по формулировке «${query}»`, async ({ page }) => {
    await page.goto('/sovety/');
    await page.getByRole('searchbox', { name: searchName }).fill(query);
    await expect(visibleCards(page).locator(`a[href="${href}"]`)).toBeVisible();
    await expect(page.locator('#advice-results')).toContainText('Найдено:');
    await expect(page.locator('[data-advice-empty]')).toBeHidden();
    await expect(page.locator('.inline-lead')).toHaveCount(0);
  });
}

test('тема уточняет запрос, а сброс возвращает весь каталог', async ({ page }) => {
  await page.goto('/sovety/');
  const total = await page.locator('#advice-catalog .service-card').count();
  await page.getByText('Лак и масло', { exact: true }).click();
  await expect(page.getByRole('radio', { name: 'Лак и масло', exact: true })).toBeChecked();
  await page.getByRole('searchbox', { name: searchName }).fill('липнет');
  await expect(visibleCards(page)).toHaveCount(1);
  await expect(visibleCards(page).getByRole('link')).toHaveAttribute('href', '/sovety/pochemu-lak-na-parkete-lipnet-posle-lakirovki/');
  await page.getByRole('button', { name: 'Сбросить поиск' }).click();
  await expect(page.getByRole('searchbox', { name: searchName })).toBeFocused();
  await expect(page.getByRole('radio', { name: 'Все темы', exact: true })).toBeChecked();
  await expect(visibleCards(page)).toHaveCount(total);
});

test('выбор темы работает с клавиатуры и не смешивает сколы со словом «сколько»', async ({ page }) => {
  await page.goto('/sovety/');
  await page.getByRole('radio', { name: 'Все темы', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('radio', { name: 'Скрип и щели', exact: true })).toBeChecked();
  await expect(visibleCards(page).locator('a[href="/sovety/pochemu-skripit-parket/"]')).toBeVisible();
  await page.getByText('Вода и повреждения', { exact: true }).click();
  await expect(visibleCards(page).locator('a[href="/sovety/skoly-na-parkete-chto-delat/"]')).toBeVisible();
  await expect(page.locator('#advice-catalog a[href="/sovety/skolko-sohnet-lak-na-parkete/"]')).toBeHidden();
});

test('пустая выдача предлагает сброс и прямую связь с Иваном', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto('/sovety/');
  await page.getByText('Сушка и уход', { exact: true }).click();
  await page.getByRole('searchbox', { name: searchName }).fill('неизвестныйдефект');
  await expect(visibleCards(page)).toHaveCount(0);
  const empty = page.locator('[data-advice-empty]');
  await expect(empty).toBeVisible();
  await expect(empty.getByRole('link', { name: 'Обсудить пол с Иваном' })).toHaveAttribute('href', 'tel:+79009267929');
  await expect(empty.getByRole('link', { name: 'Оставить обращение' })).toHaveAttribute('href', '/zayavka/');
  await page.getByRole('button', { name: 'Сбросить поиск' }).click();
  await expect(empty).toBeHidden();
  await expect(visibleCards(page)).toHaveCount(74);
});

test('возврат из статьи восстанавливает запрос и выбранную тему', async ({ page }) => {
  await page.goto('/sovety/');
  await page.getByText('Вода и повреждения', { exact: true }).click();
  await page.getByRole('searchbox', { name: searchName }).fill('затопили паркет');
  await visibleCards(page).locator('a[href="/sovety/parket-posle-vody/"]').click();
  await expect(page).toHaveURL(/\/sovety\/parket-posle-vody\/$/);
  await page.goBack();
  await expect(page.getByRole('searchbox', { name: searchName })).toHaveValue('затопили паркет');
  await expect(page.getByRole('radio', { name: 'Вода и повреждения', exact: true })).toBeChecked();
  await expect(visibleCards(page).locator('a[href="/sovety/parket-posle-vody/"]')).toBeVisible();
  await expect(page.locator('#advice-results')).toContainText('Найдено:');
});

test('поисковый текст остаётся в браузере и не попадает в URL, аналитику или хранилища', async ({ page }) => {
  const privateQuery = 'PRIVATE-SEARCH-Иван-89001234567-улица-Тестовая';
  const requests = [];
  page.on('request', request => requests.push([request.url(), request.postData()]));
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__searchYm = [];
    window.ym = (...args) => window.__searchYm.push(args);
  });
  await page.goto('/sovety/');
  await page.getByRole('searchbox', { name: searchName }).fill(privateQuery);
  await expect(page.locator('#advice-results')).toContainText('Ничего не найдено');
  const snapshot = await page.evaluate(() => ({
    url: location.href,
    dataLayer: window.dataLayer,
    ym: window.__searchYm,
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage)
  }));
  expect(JSON.stringify(snapshot)).not.toContain(privateQuery);
  expect(JSON.stringify(requests)).not.toContain(privateQuery);
  expect(JSON.stringify(requests)).not.toContain(encodeURIComponent(privateQuery));
});

for (const width of [320, 1440]) {
  test(`каталог ${width}px: фильтры доступны, карточки помещаются на экране`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/sovety/');
    await page.getByText('Вода и повреждения', { exact: true }).click();
    await expect(visibleCards(page).locator('a[href="/sovety/parket-posle-vody/"]')).toBeVisible();
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    expect(axe.violations).toEqual([]);
    const bounds = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
    expect(bounds.content).toBeLessThanOrEqual(bounds.viewport + 1);
    const screenshot = testInfo.outputPath(`advice-discovery-${width}.png`);
    await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
    await testInfo.attach('Раздел советов с выбранной темой', { path: screenshot, contentType: 'image/png' });
  });
}

test('без JavaScript доступны все материалы и быстрые ссылки на ситуации', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto('/sovety/');
  await expect(page.locator('[data-advice-search]')).toBeHidden();
  await expect(page.locator('#advice-catalog .service-card')).toHaveCount(74);
  await page.locator('.advice-shortcuts summary').click();
  await page.getByRole('navigation', { name: 'С чего начать', exact: true }).getByRole('link', { name: 'Паркет после воды', exact: true }).click();
  await expect(page).toHaveURL(/\/sovety\/parket-posle-vody\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Паркет после воды');
  await expect(page.locator('.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
  await context.close();
});
