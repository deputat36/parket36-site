import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false });

const selectors = [
  'header.topbar',
  'section.final-cta',
  'footer.footer',
  'div.mobile-cta'
];

async function readShell(page, path) {
  await page.goto(path);
  const shell = {};
  for (const selector of selectors) {
    const locator = page.locator(selector);
    await expect(locator).toHaveCount(1);
    shell[selector] = await locator.evaluate(element => element.outerHTML);
  }
  return shell;
}

test('главная и форма используют одинаковую полную общую оболочку', async ({ page }) => {
  const home = await readShell(page, '/');
  const request = await readShell(page, '/zayavka/');

  expect(request).toEqual(home);
  await expect(page.locator('a[href="tel:+79009267929"]').first()).toBeVisible();
  await expect(page.locator('section.final-cta a[href="#request"]')).toBeVisible();
});

test('страницы основной навигации используют профильные header, footer и mobile CTA', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const canonicalFooter = await page.locator('footer.footer').evaluate(element => element.outerHTML);

  for (const profile of [
    { path: '/uslugi/', activeHref: '/uslugi/' },
    { path: '/ceny/', activeHref: '/ceny/' },
    {
      path: '/o-mastere/',
      activeHref: '/o-mastere/',
      finalCtaHeading: 'Есть задача по полу?'
    },
    {
      path: '/portfolio/',
      activeHref: '/portfolio/',
      finalCtaHeading: 'Покажите свою ситуацию по полу'
    },
    {
      path: '/sovety/',
      activeHref: '/sovety/',
      finalCtaHeading: 'Не нашли точный ответ?'
    },
    {
      path: '/kontakty/',
      activeHref: '/kontakty/',
      requestHref: '#callback',
      requestLabel: 'Обратный звонок',
      finalCtaHeading: 'Обсудите паркет в Воронеже или области напрямую с Иваном'
    }
  ]) {
    await page.goto(profile.path);

    await expect(page.locator('header.topbar')).toHaveCount(1);
    await expect(page.locator('footer.footer')).toHaveCount(1);
    await expect(page.locator('div.mobile-cta')).toHaveCount(1);
    await expect(page.locator('section.final-cta')).toHaveCount(1);

    const activeLink = page.locator(`header.topbar nav a[href="${profile.activeHref}"]`);
    await expect(activeLink).toHaveClass(/active/);
    await expect(activeLink).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('header.topbar nav a[aria-current="page"]')).toHaveCount(1);

    const footer = await page.locator('footer.footer').evaluate(element => element.outerHTML);
    expect(footer).toBe(canonicalFooter);

    await expect(page.locator('div.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
    const requestHref = profile.requestHref ?? '/zayavka/';
    const requestLabel = profile.requestLabel ?? 'Оценка по фото';
    const requestAction = page.locator(`div.mobile-cta a[href="${requestHref}"]`);
    await expect(requestAction).toBeVisible();
    await expect(requestAction).toHaveText(requestLabel);
    await expect(page.locator('div.mobile-cta a[href="#request"]')).toHaveCount(0);

    if (profile.requestHref === '#callback') {
      await expect(page.locator('section#callback')).toHaveCount(1);
    }

    if (profile.finalCtaHeading) {
      await expect(page.locator('section.final-cta h2')).toHaveText(profile.finalCtaHeading);
      expect(await page.content()).not.toContain('<!-- shared-shell:final-cta -->');
    }
  }
});

test('вспомогательные страницы используют общую оболочку без ложного активного пункта', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const canonicalFooter = await page.locator('footer.footer').evaluate(element => element.outerHTML);

  for (const profile of [
    {
      path: '/resheniya/',
      finalCtaHeading: 'Не уверены, какой сценарий выбрать?'
    },
    {
      path: '/voprosy-i-otvety/',
      finalCtaHeading: 'Остался вопрос по вашему полу?'
    },
    {
      path: '/kak-rabotaem/',
      finalCtaHeading: 'Готовы начать с правильных данных?'
    }
  ]) {
    await page.goto(profile.path);

    await expect(page.locator('header.topbar')).toHaveCount(1);
    await expect(page.locator('footer.footer')).toHaveCount(1);
    await expect(page.locator('div.mobile-cta')).toHaveCount(1);
    await expect(page.locator('section.final-cta')).toHaveCount(1);
    await expect(page.locator('header.topbar nav a.active')).toHaveCount(0);
    await expect(page.locator('header.topbar nav a[aria-current="page"]')).toHaveCount(0);

    const footer = await page.locator('footer.footer').evaluate(element => element.outerHTML);
    expect(footer).toBe(canonicalFooter);

    await expect(page.locator('div.mobile-cta a[href="tel:+79009267929"]')).toBeVisible();
    const requestAction = page.locator('div.mobile-cta a[href="/zayavka/"]');
    await expect(requestAction).toBeVisible();
    await expect(requestAction).toHaveText('Оценка по фото');
    await expect(page.locator('div.mobile-cta a[href="#request"]')).toHaveCount(0);

    await expect(page.locator('section.final-cta h2')).toHaveText(profile.finalCtaHeading);
    expect(await page.content()).not.toContain('<!-- shared-shell:final-cta -->');
  }
});

test('основные услуги используют общую шапку и mobile CTA, сохраняя тематический футер', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  for (const profile of [
    {
      path: '/uslugi/ciklevka-parketa/',
      finalCtaHeading: 'Старый пол может выглядеть лучше без полной замены',
      footerText: 'Циклёвка, реставрация, ремонт паркета и деревянных полов.'
    },
    {
      path: '/uslugi/restavraciya-parketa/',
      finalCtaHeading: 'Старый паркет не всегда нужно менять',
      footerText: 'Реставрация, циклёвка, ремонт паркета и деревянных полов.'
    },
    {
      path: '/uslugi/shlifovka-doshchatogo-pola/',
      finalCtaHeading: 'Старый дощатый пол можно не менять сразу',
      footerText: 'Паркет, доска и деревянные полы.'
    }
  ]) {
    await page.goto(profile.path);

    await expect(page.locator('header.topbar')).toHaveCount(1);
    await expect(page.locator('footer.footer')).toHaveCount(1);
    await expect(page.locator('div.mobile-cta')).toHaveCount(1);
    await expect(page.locator('section.final-cta')).toHaveCount(1);

    const activeLink = page.locator('header.topbar nav a[href="/uslugi/"]');
    await expect(activeLink).toHaveClass(/active/);
    await expect(activeLink).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('header.topbar nav a[aria-current="page"]')).toHaveCount(1);

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
