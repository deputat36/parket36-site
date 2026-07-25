import { expect, test } from '@playwright/test';

const staleClaims = [
  'заявка уйдёт Ивану',
  'сайт отправит заявку Ивану',
  'Форма отправит заявку Ивану через защищённую форму',
  'заявка передаётся Ивану через защищённую форму',
  'Заявка отправляется Ивану через защищённую форму',
  'Иван получит заявку через ту же защищённую систему',
  'Заявка отправлена Ивану',
  'фотографии пола отдельными сообщениями',
  'отправить фото отдельными сообщениями',
  'Фотографии отправлю отдельными сообщениями',
  'Фотографии и видео всё равно отправляются отдельными сообщениями',
  'отправьте его Ивану вместе с фото',
  'отправьте его Ивану вместе с фотографиями пола',
  'приложите к нему фотографии пола'
];

async function expectNoStaleClaims(page) {
  const text = await page.locator('body').innerText();
  for (const claim of staleClaims) expect(text).not.toContain(claim);
}

test('главная не обещает доставку без подтверждения', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('#request')).toContainText('Форма попробует сохранить заявку в защищённой системе');
  await expect(page.locator('#request')).toContainText('Если уведомление Ивану не подтвердится');
  const disclosure = page.locator('#request-form .form-help').last();
  await expect(disclosure).toContainText('сразу появится кнопка звонка');
  await expect(disclosure).toContainText('Способ передачи фото согласуйте с Иваном');
  await expectNoStaleClaims(page);
});

test('страница оценки различает сохранение, уведомление и передачу фото', async ({ page }) => {
  await page.goto('/zayavka/');

  await expect(page.getByRole('heading', { name: 'Заполните форму — получите понятный следующий шаг' })).toBeVisible();
  await expect(page.locator('.subhero')).toContainText('После связи Иван подскажет, каким способом передать фотографии пола');
  await expect(page.locator('#request')).toContainText('сервис попробует сохранить заявку');
  await expect(page.locator('#request')).toContainText('После связи Иван подскажет, каким способом передать фотографии');
  await expect(page.locator('#request')).toContainText('Если автоматическое уведомление не подтвердится');

  const disclosure = page.locator('#request-form .form-help').last();
  await expect(disclosure).toContainText('Форма попробует сохранить заявку в защищённой системе');
  await expect(disclosure).toContainText('Способ передачи фото согласуйте с Иваном');
  await expect(disclosure).toContainText('сразу появится кнопка звонка');
  await expectNoStaleClaims(page);
});

test('полная заявка объясняет следующий шаг без выдуманного мессенджера', async ({ page }) => {
  await page.goto('/zayavka/');

  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-area').fill('18 м²');
  await page.locator('#request-photos').selectOption({ label: 'Есть общий вид и дефекты крупно' });
  await page.locator('#request-task').fill('Нужно оценить старый паркет, щели и состояние покрытия перед ремонтом.');
  await page.locator('#request-contact').fill('Алексей +7 900 000-00-00');

  const readiness = page.locator('[data-request-readiness="true"]');
  await expect(readiness).toContainText('5 из 5');
  await expect(readiness).toContainText('После связи Иван подскажет, как передать фотографии и видео');
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
