import { expect, test } from '@playwright/test';

const leadEndpoint = '**/functions/v1/parket-public-lead';

const problemTopics = [
  {
    path: '/sovety/parket-posle-vody/',
    key: 'posle-vody',
    label: 'паркет после воды или протечки',
    task: 'Интересует состояние паркета после воды или протечки. Прошу перезвонить, уточнить, что делать сейчас, и подсказать, какие фотографии или видео подготовить.'
  },
  {
    path: '/sovety/pochemu-skripit-parket/',
    key: 'skrip',
    label: 'скрип паркета или деревянного пола',
    task: 'Интересует скрип паркета или деревянного пола. Прошу перезвонить, уточнить масштаб и подсказать, какое видео и фотографии подготовить для диагностики.'
  },
  {
    path: '/sovety/shcheli-v-parkete/',
    key: 'shcheli',
    label: 'щели и подвижность паркета',
    task: 'Интересуют щели или подвижность паркета. Прошу перезвонить, уточнить состояние пола и подсказать, какие фотографии или видео подготовить.'
  }
];

async function captureCallbackSignals(page) {
  await page.addInitScript(() => {
    window.dataLayer = [];
    window.__callbackOpen = null;
    window.__callbackRequest = null;
    window.addEventListener('parket36:callback-open', event => {
      window.__callbackOpen = event.detail;
    });
    window.addEventListener('parket36:callback-request', event => {
      window.__callbackRequest = event.detail;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => {} }
    });
  });
}

test('прямой вход на контакты сохраняет общую тему', async ({ page }) => {
  await captureCallbackSignals(page);
  await page.goto('/kontakty/#callback');

  await expect(page.locator('#callback')).toBeInViewport();
  await expect(page.locator('#callback-topic-context')).toHaveCount(0);
  await expect(page.locator('#request-form')).not.toHaveAttribute('data-callback-topic', /.+/);
  await expect(page.locator('#request-task')).toHaveValue(
    'Прошу перезвонить и проконсультировать по состоянию паркета или деревянного пола. Детали и фотографии сообщу после звонка.'
  );
  await expect.poll(() => page.evaluate(() => window.__callbackOpen)).toMatchObject({
    type: 'callback-open',
    trigger: 'hash-entry',
    topic: 'general',
    topicSource: 'general',
    attribution: { source: 'direct', landing: '/kontakty/' }
  });
});

test('first-touch восстанавливает тему без внутреннего referrer', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('parket36_attribution', JSON.stringify({
      source: 'print_qr',
      medium: 'offline',
      campaign: 'voronezh_parquet_launch',
      content: 'price_flyer',
      term: '',
      landing: '/ceny/',
      firstSeen: '2026-07-13T10:00:00.000Z'
    }));
  });
  await captureCallbackSignals(page);
  await page.goto('/kontakty/#callback');

  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic', 'stoimost');
  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic-source', 'first-touch');
  await expect.poll(() => page.evaluate(() => window.__callbackOpen)).toMatchObject({
    topic: 'stoimost',
    topicSource: 'first-touch',
    attribution: { source: 'print_qr', landing: '/ceny/' }
  });
});

test('переход со стоимости показывает тему бюджета', async ({ page }) => {
  await captureCallbackSignals(page);
  await page.goto('/ceny/?utm_source=vk&utm_medium=social&utm_campaign=voronezh_parquet_launch&utm_content=price_topic');
  await page.locator('a.btn[href="/kontakty/#callback"]').click();

  await expect(page).toHaveURL(/\/kontakty\/#callback$/);
  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic', 'stoimost');
  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic-source', 'referrer');
  await expect(page.locator('#callback-topic-context')).toHaveText('Тема обращения: стоимость паркетных работ.');
  await expect(page.locator('#request-task')).toHaveValue(
    'Интересует предварительное обсуждение стоимости паркетных работ. Прошу перезвонить, уточнить состояние пола, объём и данные, необходимые для ориентира.'
  );
  await expect.poll(() => page.evaluate(() => window.__callbackOpen)).toMatchObject({
    topic: 'stoimost',
    topicSource: 'referrer',
    trigger: 'hash-entry',
    attribution: { source: 'vk', landing: '/ceny/' }
  });

  const openEvent = await page.evaluate(() => window.dataLayer.find(item => item.event === 'parket36_callback_open'));
  expect(openEvent).toMatchObject({
    callback_topic: 'stoimost',
    callback_topic_source: 'referrer'
  });
});

test('переход с циклёвки отправляет конкретную задачу Ивану', async ({ page }) => {
  let payload;
  await page.route(leadEndpoint, async route => {
    payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, request_id: payload.request_id, lead_id: 803 })
    });
  });
  await captureCallbackSignals(page);

  await page.goto('/uslugi/ciklevka-parketa/?utm_source=avito&utm_medium=classified&utm_campaign=voronezh_parquet_launch&utm_content=cyclevka_topic');
  await page.locator('a[href="/kontakty/#callback"]').first().click();

  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic', 'cyclevka');
  await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic-source', 'referrer');
  await expect(page.locator('#callback-topic-context')).toHaveText('Тема обращения: циклёвка и шлифовка паркета.');
  await page.locator('#request-location').fill('Воронеж');
  await page.locator('#request-callback').fill('После 18:00');
  await page.locator('#request-contact').fill('Сергей, +7 900 111-22-33');
  await page.getByRole('button', { name: 'Заказать обратный звонок' }).click();

  expect(payload).toMatchObject({
    service: 'Обратный звонок по паркетным работам',
    task: 'Интересует циклёвка или шлифовка паркета. Прошу перезвонить, уточнить состояние пола и подсказать, какие фотографии или видео подготовить.',
    page: '/kontakty/',
    utm_source: 'avito',
    utm_medium: 'classified'
  });
  await expect.poll(() => page.evaluate(() => window.__callbackRequest)).toMatchObject({
    type: 'callback-request',
    topic: 'cyclevka',
    topicSource: 'referrer',
    attribution: { landing: '/uslugi/ciklevka-parketa/' }
  });

  const requestEvent = await page.evaluate(() => window.dataLayer.find(item => item.event === 'parket36_callback_request'));
  expect(requestEvent).toMatchObject({
    callback_topic: 'cyclevka',
    callback_topic_source: 'referrer'
  });
});

for (const topic of problemTopics) {
  test(`${topic.path} передаёт конкретную тему обратного звонка`, async ({ page }) => {
    await captureCallbackSignals(page);
    await page.goto(`${topic.path}?utm_source=organic&utm_medium=seo&utm_campaign=problem_pages&utm_content=${topic.key}`);
    await page.locator('a[href="/kontakty/#callback"]').first().click();

    await expect(page).toHaveURL(/\/kontakty\/#callback$/);
    await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic', topic.key);
    await expect(page.locator('#request-form')).toHaveAttribute('data-callback-topic-source', 'referrer');
    await expect(page.locator('#callback-topic-context')).toHaveText(`Тема обращения: ${topic.label}.`);
    await expect(page.locator('#request-task')).toHaveValue(topic.task);
    await expect.poll(() => page.evaluate(() => window.__callbackOpen)).toMatchObject({
      topic: topic.key,
      topicSource: 'referrer',
      attribution: {
        source: 'organic',
        medium: 'seo',
        campaign: 'problem_pages',
        content: topic.key,
        landing: topic.path
      }
    });

    const openEvent = await page.evaluate(() => window.dataLayer.find(item => item.event === 'parket36_callback_open'));
    expect(openEvent).toMatchObject({
      callback_topic: topic.key,
      callback_topic_source: 'referrer'
    });
  });
}
