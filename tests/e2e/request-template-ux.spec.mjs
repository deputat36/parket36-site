import { expect, test } from '@playwright/test';

test('выбор другого шаблона заменяет старый, а повторный выбор не создаёт дубль', async ({ page }) => {
  await page.goto('/zayavka/');

  const task = page.locator('#request-task');
  const cycle = page.getByRole('button', { name: 'Циклёвка', exact: true });
  const restore = page.getByRole('button', { name: 'Реставрация', exact: true });
  const cycleTemplate = await cycle.getAttribute('data-request-template');
  const restoreTemplate = await restore.getAttribute('data-request-template');

  await cycle.click();
  await expect(task).toHaveValue(cycleTemplate);

  await restore.click();
  await expect(task).toHaveValue(restoreTemplate);

  await restore.click();
  await expect(task).toHaveValue(restoreTemplate);
});

test('смена ситуации сохраняет личные пояснения без старого шаблона', async ({ page }) => {
  await page.goto('/zayavka/');

  const task = page.locator('#request-task');
  const first = page.getByRole('button', { name: 'Пол / паркет' });
  const second = page.getByRole('button', { name: 'После воды' });
  const firstTemplate = await first.getAttribute('data-request-template');
  const secondTemplate = await second.getAttribute('data-request-template');
  const note = 'Дополнительно: комната на втором этаже, доски возле окна темнее.';

  await first.click();
  await task.fill(`${firstTemplate}\n\n${note}`);
  await second.click();

  await expect(task).toHaveValue(`${secondTemplate}\n\n${note}`);
  expect(await task.inputValue()).not.toContain(firstTemplate);

  await second.click();
  await expect(task).toHaveValue(`${secondTemplate}\n\n${note}`);
});

test('шаблон обновляет индикатор готовности и счётчик символов', async ({ page }) => {
  await page.goto('/zayavka/');

  const task = page.locator('#request-task');
  const panel = page.locator('[data-request-readiness]');
  const counter = page.locator('[data-lead-character-counter="request-task"]');
  const button = page.getByRole('button', { name: 'После арендаторов' });

  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('0 из 5');
  await expect(counter).toHaveText('0 / 3000');

  await button.click();
  const template = await button.getAttribute('data-request-template');
  await expect(task).toHaveValue(template);
  await expect(panel.locator('[data-request-readiness-score]')).toHaveText('1 из 5');
  await expect(counter).toHaveText(`${template.length} / 3000`);
  await expect(panel.locator('[data-readiness-key="task"]')).toHaveClass(/is-complete/);
});

test('кнопка шаблона срабатывает от клавиатуры и перемещает фокус в описание', async ({ page }) => {
  await page.goto('/zayavka/');

  const button = page.getByRole('button', { name: 'Укладка', exact: true });
  await button.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#request-task')).toHaveValue(/Нужна укладка/);
  await expect(page.locator('#request-task')).toBeFocused();
});

test('шаблоны не должны удалять описание, если пользователь ввёл его без выбора шаблона', async ({ page }) => {
  await page.goto('/zayavka/');

  const task = page.locator('#request-task');
  const note = 'Штучный паркет в гостиной, нужно убрать глубокие царапины возле входа.';
  await task.fill(note);

  const template = page.getByRole('button', { name: 'Циклёвка', exact: true });
  await template.click();

  expect(await task.inputValue()).toContain(note);
  expect((await task.inputValue()).startsWith(await template.getAttribute('data-request-template'))).toBe(true);
});
