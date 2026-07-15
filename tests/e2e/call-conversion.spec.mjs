import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

const phoneHref = 'tel:+79009267929';

test('desktop показывает понятный телефон в шапке и call-first финальный CTA', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/');

  const headerPhone = page.locator('header.topbar a.phone--header');
  await expect(headerPhone).toBeVisible();
  await expect(headerPhone).toHaveAttribute('href', phoneHref);
  await expect(headerPhone).toHaveAttribute('data-call-source', 'header');
  await expect(headerPhone.locator('.phone__label')).toHaveText('Позвонить Ивану');
  await expect(headerPhone.locator('.phone__number')).toHaveText('8 (900) 926-79-29');

  await expect(page.locator('.mobile-cta')).not.toBeVisible();
  await expect(page.locator('section.final-cta h2')).toHaveText(
    'Не знаете, с чего начать с полом? Позвоните Ивану'
  );
  await expect(page.locator('section.final-cta a[data-call-source="final-cta"]')).toHaveAttribute(
    'href',
    phoneHref
  );

  const heroIcon = await page.locator('.hero__visual--plan .photo-slot--large').evaluate(
    element => getComputedStyle(element, '::before').content
  );
  expect(heroIcon).toContain('☎');
});

test('планшетный диапазон всегда сохраняет фиксированный звонок', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 900 });
  await page.goto('/');

  await expect(page.locator('header.topbar .topbar__contacts')).not.toBeVisible();

  const sticky = page.locator('.mobile-cta');
  await expect(sticky).toBeVisible();
  await expect(sticky).toHaveAttribute('aria-label', 'Быстрые действия');
  await expect(sticky.locator(`a[href="${phoneHref}"]`)).toBeVisible();
  await expect(sticky.locator(`a[href="${phoneHref}"]`)).toHaveText('Позвонить Ивану');
  await expect(sticky.locator('a[href="#request"]')).toHaveText('Оценка по фото');

  const styles = await sticky.evaluate(element => {
    const style = getComputedStyle(element);
    return { position: style.position, display: style.display, width: style.width };
  });
  expect(styles.position).toBe('fixed');
  expect(styles.display).toBe('grid');
  expect(Number.parseFloat(styles.width)).toBeGreaterThan(400);

  const bodyPadding = await page.locator('body').evaluate(
    element => Number.parseFloat(getComputedStyle(element).paddingBottom)
  );
  expect(bodyPadding).toBeGreaterThanOrEqual(80);
});

test('узкий мобильный экран сохраняет обе цели и безопасный нижний отступ', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  const sticky = page.locator('.mobile-cta');
  await expect(sticky).toBeVisible();
  await expect(sticky.locator('a')).toHaveCount(2);
  await expect(sticky.locator(`a[href="${phoneHref}"]`)).toBeVisible();
  await expect(sticky.locator('a[href="#request"]')).toBeVisible();

  const stickyBox = await sticky.boundingBox();
  expect(stickyBox).not.toBeNull();
  expect(stickyBox.width).toBeLessThanOrEqual(378);
  expect(stickyBox.x).toBeGreaterThanOrEqual(5);

  const bodyPadding = await page.locator('body').evaluate(
    element => Number.parseFloat(getComputedStyle(element).paddingBottom)
  );
  expect(bodyPadding).toBeGreaterThanOrEqual(80);
});

test('памятка звонка также сохраняет фиксированный телефон на планшете', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 900 });
  await page.goto('/pozvonit-ivanu/');

  await expect(page.locator('h1')).toHaveText('Что сказать Ивану по телефону про паркет');
  await expect(page.locator(`a[href="${phoneHref}"]`)).toHaveCount(7);
  await expect(page.locator('.mobile-cta')).toBeVisible();
  await expect(page.locator(`.mobile-cta a[href="${phoneHref}"]`)).toBeVisible();
});
