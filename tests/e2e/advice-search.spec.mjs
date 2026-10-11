import { expect, test } from '@playwright/test';

test('поиск по советам фильтрует существующие карточки и обновляет счётчик', async ({ page }) => {
  await page.goto('/sovety/');

  const search = page.getByRole('search', { name: 'Поиск по советам о паркете' });
  const input = page.getByRole('searchbox', { name: 'Найдите совет по вашей проблеме' });
  const cards = page.locator('main .services-grid .service-card');
  const total = await cards.count();

  expect(total).toBeGreaterThan(60);
  await expect(search).toBeVisible();
  await expect(page.locator('#advice-results')).toContainText(`Все советы: ${total}`);
  await expect(page.getByRole('button', { name: 'Сбросить поиск' })).toBeHidden();

  await input.fill('скрип');
  const visible = cards.filter({ visible: true });
  const count = await visible.count();
  expect(count).toBeGreaterThan(0);
  expect(count).toBeLessThan(total);
  for (const text of await visible.allTextContents()) {
    expect(text.toLocaleLowerCase('ru-RU')).toContain('скрип');
  }
  await expect(page.locator('#advice-results')).toContainText(`Найдено: ${count}`);

  await input.fill('несуществующаянеисправность');
  await expect(cards.filter({ visible: true })).toHaveCount(0);
  await expect(page.locator('#advice-results')).toContainText('Ничего не найдено');

  await page.getByRole('button', { name: 'Сбросить поиск' }).click();
  await expect(input).toHaveValue('');
  await expect(input).toBeFocused();
  await expect(cards.filter({ visible: true })).toHaveCount(total);
});

test('мобильный поиск не скрывает навигацию и ссылки по проблемам', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/sovety/');
  const input = page.getByRole('searchbox', { name: 'Найдите совет по вашей проблеме' });
  await expect(input).toBeVisible();
  await input.fill('щели');
  const firstLink = page.locator('main .services-grid .service-card:not([hidden]) a').first();
  await expect(firstLink).toBeVisible();
  await expect(firstLink).toHaveAttribute('href', /\/sovety\//);
  await expect(page.locator('a[href="tel:+79009267929"]').first()).toBeVisible();
});

test('если скрипт поиска не загрузился, список статей остаётся доступным', async ({ page }) => {
  await page.route('**/js/advice-search*.js', route => route.abort());
  await page.goto('/sovety/');
  await expect(page.locator('[data-advice-search]')).toBeHidden();
  const cards = page.locator('main .services-grid .service-card');
  expect(await cards.count()).toBeGreaterThan(60);
  await expect(cards.first()).toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Советы');
});
