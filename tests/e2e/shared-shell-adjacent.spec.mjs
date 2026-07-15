import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

test('смежные noindex-услуги используют только общую шапку и mobile CTA', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  for (const profile of [
    {
      path: '/uslugi/demontazh/',
      finalCtaHeading: 'Начните с фото пола и зон, которые мешают доступу',
      footerText: 'Паркет и деревянные полы — основное направление. Подготовительный демонтаж обсуждается только если он нужен для работ с полом.'
    },
    {
      path: '/uslugi/elektrika/',
      finalCtaHeading: 'Опишите электрику отдельным пунктом',
      footerText: 'Паркет и деревянные полы — основное направление. Электрика фиксируется отдельным вопросом.'
    },
    {
      path: '/uslugi/melkiy-remont/',
      finalCtaHeading: 'Покажите пол и дополнительные вопросы одним сообщением',
      footerText: 'Паркет и деревянные полы — основное направление. Мелкие вопросы фиксируются отдельно.'
    },
    {
      path: '/uslugi/muzh-na-chas/',
      finalCtaHeading: 'Сначала покажите пол, затем дополнительные вопросы',
      footerText: 'Паркет и деревянные полы — основное направление. Мелкие вопросы фиксируются отдельно.'
    },
    {
      path: '/uslugi/otdelka/',
      finalCtaHeading: 'Опишите отделку отдельным пунктом',
      footerText: 'Паркет и деревянные полы — основное направление. Отделка фиксируется отдельным вопросом.'
    },
    {
      path: '/uslugi/pereezdy/',
      finalCtaHeading: 'Покажите, что мешает доступу к полу',
      footerText: 'Паркет и деревянные полы — основное направление. Перенос вещей фиксируется как вопрос доступа к полу.'
    },
    {
      path: '/uslugi/santehnika/',
      finalCtaHeading: 'Опишите сантехнику отдельным пунктом',
      footerText: 'Паркет и деревянные полы — основное направление. Сантехника фиксируется отдельным вопросом.'
    },
    {
      path: '/uslugi/sborka-mebeli/',
      finalCtaHeading: 'Покажите мебель как часть доступа к полу',
      footerText: 'Паркет и деревянные полы — основное направление. Мебель фиксируется как вопрос доступа к полу.'
    },
    {
      path: '/uslugi/vyvoz-musora/',
      finalCtaHeading: 'Сфотографируйте пол и всё, что связано с подготовкой',
      footerText: 'Паркет и деревянные полы — основное направление. Вынос остатков обсуждается только как дополнение к работам с полом.'
    }
  ]) {
    await page.goto(profile.path);

    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
    await expect(page.locator('meta[property="og:type"]')).toHaveAttribute('content', 'website');
    await expect(page.locator('header.topbar')).toHaveCount(1);
    await expect(page.locator('footer.footer')).toHaveCount(1);
    await expect(page.locator('section.final-cta')).toHaveCount(1);
    await expect(page.locator('div.mobile-cta')).toHaveCount(1);
    await expect(page.locator('header.topbar nav a.active')).toHaveCount(0);
    await expect(page.locator('header.topbar nav a[aria-current="page"]')).toHaveCount(0);

    await expect(page.locator('div.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
    const requestAction = page.locator('div.mobile-cta a[href="/zayavka/"]');
    await expect(requestAction).toBeVisible();
    await expect(requestAction).toHaveText('Оценка по фото');
    await expect(page.locator('div.mobile-cta a[href="#request"]')).toHaveCount(0);

    await expect(page.locator('section.final-cta h2')).toHaveText(profile.finalCtaHeading);
    await expect(page.locator('footer.footer')).toContainText(profile.footerText);

    const content = await page.content();
    expect(content).toContain('<!-- shared-shell:header -->');
    expect(content).toContain('<!-- shared-shell:mobile-cta -->');
    expect(content).not.toContain('<!-- shared-shell:footer -->');
    expect(content).not.toContain('<!-- shared-shell:final-cta -->');
  }
});

test('старый адрес master-na-chas остаётся отдельным redirect-переходником', async ({ page }) => {
  await page.goto('/uslugi/master-na-chas/');

  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
  await expect(page.locator('meta[http-equiv="refresh"]')).toHaveAttribute(
    'content',
    '4;url=/uslugi/muzh-na-chas/'
  );
  await expect(page.locator('header.topbar nav')).toHaveCount(0);
  await expect(page.locator('section.final-cta')).toHaveCount(0);
  await expect(page.locator('footer.footer')).toHaveCount(1);
  await expect(page.locator('div.mobile-cta a[href="/zayavka/"]')).toHaveText('Оценка по фото');

  const content = await page.content();
  expect(content).not.toContain('<!-- shared-shell:header -->');
  expect(content).not.toContain('<!-- shared-shell:mobile-cta -->');
});
