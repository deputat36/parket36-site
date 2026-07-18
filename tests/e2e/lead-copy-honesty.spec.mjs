import { expect, test } from '@playwright/test';

const staleClaims = [
  'заявка уйдёт Ивану',
  'сайт отправит заявку Ивану',
  'заявка передаётся Ивану через защищённую форму',
  'Заявка отправляется Ивану через защищённую форму',
  'Иван получит заявку через ту же защищённую систему'
];

async function expectNoStaleClaims(page) {
  const text = await page.locator('body').innerText();
  for (const claim of staleClaims) expect(text).not.toContain(claim);
}

test('страница оценки различает сохранение и уведомление', async ({ page }) => {
  await page.goto('/zayavka/');

  await expect(page.getByRole('heading', { name: 'Заполните форму — получите понятный следующий шаг' })).toBeVisible();
  await expect(page.locator('#request')).toContainText('сервис попробует сохранить заявку');
  await expect(page.locator('#request')).toContainText('Если автоматическое уведомление не подтвердится');

  const disclosure = page.locator('#request-form .form-help').last();
  await expect(disclosure).toContainText('Форма попробует сохранить заявку в защищённой системе');
  await expect(disclosure).toContainText('сразу появится кнопка звонка');
  await expectNoStaleClaims(page);
});

test('callback не обещает получение заявки без подтверждения', async ({ page }) => {
  await page.goto('/kontakty/#callback');

  await expect(page.locator('.contact-card').filter({ hasText: 'Обратный звонок' })).toContainText(
    'Форма попробует сохранить контакт в защищённой системе'
  );
  const disclosure = page.locator('#request-form .form-help').last();
  await expect(disclosure).toContainText('Форма попробует сохранить номер в защищённой системе');
  await expect(disclosure).toContainText('Если уведомление Ивану не подтвердится');
  await expectNoStaleClaims(page);
});

test('политика описывает хранение отдельно от уведомления', async ({ page }) => {
  await page.goto('/politika/');

  const prose = page.locator('.prose');
  await expect(prose).toContainText('Форма пытается сохранить заявку в защищённой системе');
  await expect(prose).toContainText('подтверждено ли автоматическое уведомление Ивану');
  await expect(prose).toContainText('Успешно принятые заявки сохраняются в защищённом хранилище Supabase');
  await expectNoStaleClaims(page);
});
