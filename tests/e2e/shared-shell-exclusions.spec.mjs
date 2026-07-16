import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

const exclusions = [
  {
    path: '/404.html',
    canonical: 'https://parket36.ru/404.html',
    heading: 'Такой страницы нет, но задачу по полу можно продолжить'
  },
  {
    path: '/politika/',
    canonical: 'https://parket36.ru/politika/',
    heading: 'Обработка контактных данных'
  },
  {
    path: '/pozvonit-ivanu/',
    canonical: 'https://parket36.ru/pozvonit-ivanu/',
    heading: 'Что сказать Ивану по телефону про паркет'
  },
  {
    path: '/uslugi/master-na-chas/',
    canonical: 'https://parket36.ru/uslugi/muzh-na-chas/',
    heading: 'Этот адрес больше не является основной страницей услуг'
  }
];

test('проверенные исключения сохраняют отдельный noindex-контракт без shared markers', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  for (const exclusion of exclusions) {
    await page.goto(exclusion.path);

    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', exclusion.canonical);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(exclusion.heading);

    const content = await page.content();
    expect(content).not.toContain('<!-- shared-shell:header -->');
    expect(content).not.toContain('<!-- shared-shell:final-cta -->');
    expect(content).not.toContain('<!-- shared-shell:footer -->');
    expect(content).not.toContain('<!-- shared-shell:mobile-cta -->');
  }
});

test('памятка звонка сохраняет собственную атрибуцию CTA', async ({ page }) => {
  await page.goto('/pozvonit-ivanu/');

  await expect(page.locator('[data-call-source="phone-helper-hero"]')).toHaveCount(1);
  await expect(page.locator('[data-call-source="phone-helper-final"]')).toHaveCount(1);
  await expect(page.locator('a[href="tel:+79009267929"]')).toHaveCount(8);
});

test('legacy master-na-chas остаётся переходником на каноническую страницу', async ({ page }) => {
  await page.goto('/uslugi/master-na-chas/');

  await expect(page.locator('meta[http-equiv="refresh"]')).toHaveAttribute(
    'content',
    '4;url=/uslugi/muzh-na-chas/'
  );
  await expect(page.locator('header.topbar nav')).toHaveCount(0);
  await expect(page.locator('section.final-cta')).toHaveCount(0);
});
