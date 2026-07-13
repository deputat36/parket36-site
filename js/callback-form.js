(() => {
  const form = document.querySelector('#request-form[data-form-kind="callback"]');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!status) return;

  const ATTRIBUTION_KEY = 'parket36_attribution';
  const TOPICS_BY_LANDING = Object.freeze({
    '/ceny/': {
      key: 'stoimost',
      label: 'стоимость паркетных работ',
      task: 'Интересует предварительное обсуждение стоимости паркетных работ. Прошу перезвонить, уточнить состояние пола, объём и данные, необходимые для ориентира.'
    },
    '/uslugi/ciklevka-parketa/': {
      key: 'cyclevka',
      label: 'циклёвка и шлифовка паркета',
      task: 'Интересует циклёвка или шлифовка паркета. Прошу перезвонить, уточнить состояние пола и подсказать, какие фотографии или видео подготовить.'
    },
    '/uslugi/restavraciya-parketa/': {
      key: 'restavraciya',
      label: 'реставрация и ремонт паркета',
      task: 'Интересует реставрация или ремонт паркета. Прошу перезвонить, уточнить дефекты пола и подсказать, какие фотографии или видео подготовить.'
    }
  });

  let callbackOpenEmitted = false;
  let activeTopic = null;

  const readAttribution = () => {
    if (window.parket36Attribution) return window.parket36Attribution;
    try {
      const stored = sessionStorage.getItem(ATTRIBUTION_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  };

  const applyTopicContext = () => {
    if (activeTopic) return activeTopic;

    const attribution = readAttribution();
    const topic = TOPICS_BY_LANDING[attribution?.landing || ''];
    if (!topic) return null;

    activeTopic = topic;
    form.dataset.callbackTopic = topic.key;

    const taskField = form.querySelector('#request-task');
    if (taskField instanceof HTMLInputElement) taskField.value = topic.task;

    if (!form.querySelector('#callback-topic-context')) {
      const context = document.createElement('p');
      context.id = 'callback-topic-context';
      context.className = 'form-help callback-topic-context';
      context.textContent = `Тема обращения: ${topic.label}.`;
      const heading = form.querySelector('h3');
      if (heading) heading.insertAdjacentElement('afterend', context);
      else form.prepend(context);
    }

    return activeTopic;
  };

  const sendGoal = (goal, detail) => {
    if (typeof window.ym !== 'function' || !window.parket36MetrikaId) return;
    try {
      window.ym(window.parket36MetrikaId, 'reachGoal', goal, detail);
    } catch {
      // Analytics must never affect the callback form.
    }
  };

  const emitCallbackOpen = ({ href = '#callback', trigger = 'click' } = {}) => {
    if (callbackOpenEmitted) return;
    callbackOpenEmitted = true;

    const topic = applyTopicContext();
    const detail = {
      type: 'callback-open',
      href,
      trigger,
      topic: topic?.key || 'general',
      page: location.pathname,
      attribution: { ...(window.parket36Attribution || readAttribution()) }
    };
    window.dispatchEvent(new CustomEvent('parket36:callback-open', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_open',
        page: detail.page,
        trigger: detail.trigger,
        callback_topic: detail.topic,
        attribution: detail.attribution
      });
    }

    sendGoal('callback-open', detail);
  };

  const emitCallbackRequest = leadDetail => {
    const topic = applyTopicContext();
    const detail = {
      ...leadDetail,
      type: 'callback-request',
      topic: topic?.key || 'general'
    };
    window.dispatchEvent(new CustomEvent('parket36:callback-request', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_request',
        page: detail.page || location.pathname,
        service: detail.service || 'Обратный звонок по паркетным работам',
        callback_topic: detail.topic,
        attribution: detail.attribution || window.parket36Attribution || readAttribution()
      });
    }

    sendGoal('callback-request', detail);
  };

  document.querySelectorAll('a[href="#callback"]').forEach(link => {
    link.addEventListener('click', () => emitCallbackOpen({
      href: link.getAttribute('href') || '#callback',
      trigger: 'click'
    }));
  });

  const emitHashEntry = () => {
    if (location.hash !== '#callback') return;
    emitCallbackOpen({ href: '#callback', trigger: 'hash-entry' });
  };

  window.addEventListener('hashchange', emitHashEntry);
  window.setTimeout(() => {
    applyTopicContext();
    emitHashEntry();
  }, 0);

  window.addEventListener('parket36:lead', event => {
    if (!event.detail || !['request-submit', 'request-copy'].includes(event.detail.type)) return;

    if (event.detail.type === 'request-submit') {
      status.textContent = 'Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.';
      emitCallbackRequest(event.detail);
      return;
    }

    status.textContent = 'Автоматически отправить заявку не удалось. Текст скопирован — позвоните Ивану или используйте полную форму оценки.';
  });
})();