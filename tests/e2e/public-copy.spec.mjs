import { expect, test } from '@playwright/test';

const forbiddenCopy = [
  'Фото вместо иллюстрации',
  'Место под реальное фото',
  'Место под фото',
  'Место для фото',
  'Сюда нужен реальный кадр',
  'Места под будущие реальные фотографии',
  'будущие кейсы'
];

async function expectNoPlaceholderCopy(page) {
  const bodyText = await page.locator('body').innerText();
  for (const phrase of forbiddenCopy) {
    expect(bodyText, `Public page must not contain: ${phrase}`).not.toContain(phrase);
  }
}

test('главная объясняет, какие материалы нужны для оценки, без служебных заглушек', async ({ page }) => {
  await page.goto('/');

  await expectNoPlaceholderCopy(page);
  await expect(page.getByText('Оценка по фото', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Общий вид комнаты', { exact: true })).toBeVisible();
  await expect(page.getByText('Дефект крупно', { exact: true })).toBeVisible();
  await expect(page.getByText('Короткое видео', { exact: true })).toBeVisible();
  await expect(page.getByText('Скрип или движение', { exact: true })).toBeVisible();
});

test('страница примеров показывает типовые задачи, а не внутренний план будущих кейсов', async ({ page }) => {
  await page.goto('/portfolio/');

  await expectNoPlaceholderCopy(page);
  await expect(page).toHaveTitle(/Типовые задачи по паркету/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Типовые задачи');
  await expect(page.getByRole('heading', { name: 'Изношенный лак и потёртости' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Щели между планками' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Следы воды' })).toBeVisible();
  await expect(page.getByText(/страница не выдаёт схемы за выполненные объекты/i)).toBeVisible();
});

test('публичные SVG содержат клиентские схемы вместо указаний разработчику', async ({ request }) => {
  for (const path of ['/img/work-floor.svg', '/img/work-tools.svg', '/img/ivan-workwear.svg']) {
    const response = await request.get(path);
    expect(response.ok(), `${path} should be available`).toBeTruthy();
    const svg = await response.text();
    for (const phrase of forbiddenCopy) {
      expect(svg, `${path} must not contain: ${phrase}`).not.toContain(phrase);
    }
  }

  const floor = await (await request.get('/img/work-floor.svg')).text();
  expect(floor).toContain('Оценка паркета по фото');

  const tools = await (await request.get('/img/work-tools.svg')).text();
  expect(tools).toContain('От фотографии до решения');

  const master = await (await request.get('/img/ivan-workwear.svg')).text();
  expect(master).toContain('Мастер Иван');
  expect(master).toContain('8 (900) 926-79-29');
});
