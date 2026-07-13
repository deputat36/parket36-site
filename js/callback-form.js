(() => {
  const form = document.querySelector('#request-form[data-form-kind="callback"]');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!status) return;

  const ATTRIBUTION_KEY = 'parket36_attribution';
  const UTM_KEYS = Object.freeze([
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_content',
    'utm_term'
  ]);
  const TOPICS_BY_PATH = Object.freeze({
    '/ceny/': {
      key: 'stoimost',
      label: 'стоимость паркетных работ',
      task: 'Интересует предварительное обсуждение стоимости паркетных работ. Прошу перезвонить, уточнить состояние пола, объём и данные, необходимые для ориентира.'
    },
    '/uslugi/': {
      key: 'podbor-uslugi',
      label: 'подбор подходящей работы по полу',
      task: 'Не знаю, какая работа нужна для паркета или деревянного пола. Прошу перезвонить, уточнить симптомы и подсказать, с чего начать и какие фотографии или видео подготовить.'
    },
    '/uslugi/parket-i-poly/': {
      key: 'diagnostika',
      label: 'диагностика паркета и деревянного пола',
      task: 'Нужна предварительная диагностика паркета или деревянного пола. Прошу перезвонить, уточнить состояние покрытия, скрип, щели или другие дефекты и подсказать необходимые фотографии или видео.'
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
    },
    '/sovety/parket-posle-vody/': {
      key: 'posle-vody',
      label: 'паркет после воды или протечки',
      task: 'Интересует состояние паркета после воды или протечки. Прошу перезвонить, уточнить, что делать сейчас, и подсказать, какие фотографии или видео подготовить.'
    },
    '/sovety/pochemu-skripit-parket/': {
      key: 'skrip',
      label: 'скрип паркета или деревянного пола',
      task: 'Интересует скрип паркета или деревянного пола. Прошу перезвонить, уточнить масштаб и подсказать, какое видео и фотографии подготовить для диагностики.'
    },
    '/sovety/shcheli-v-parkete/': {
      key: 'shcheli',
      label: 'щели и подвижность паркета',
      task: 'Интересуют щели или подвижность паркета. Прошу перезвонить, уточнить состояние пола и подсказать, какие фотографии или видео подготовить.'
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

  const readCurrentUrlAttribution = () => {
    const params = new URLSearchParams(location.search);
    if (!UTM_KEYS.some(key => params.has(key))) return null;

    let referrerHost = '';
    if (document.referrer) {
      try {
        referrerHost = new URL(document.referrer).hostname;
      } catch {
        referrerHost = '';
      }
    }

    return {
      source: params.get('utm_source') || referrerHost || 'direct',
      medium: params.get('utm_medium') || '',
      campaign: params.get('utm_campaign') || '',
      content: params.get('utm_content') || '',
      term: params.get('utm_term') || '',
      landing: location.pathname,
      firstSeen: new Date().toISOString()
    };
  };

  const getEventAttribution = () => {
    const attribution = readAttribution();
    if (attribution && Object.keys(attribution).length) return attribution;

    const currentUrlAttribution = readCurrentUrlAttribution();
    if (currentUrlAttribution) return currentUrlAttribution;

    return {
      source: 'direct',
      medium: '',
      campaign: '',
      content: '',
      term: '',
      landing: location.pathname
    };
  };

  const readInternalReferrerPath = () => {
    if (!document.referrer) return '';
    try {
      const referrer = new URL(document.referrer);
      return referrer.origin === location.origin ? referrer.pathname : '';
    } catch {
      return '';
    }
  };

  const resolveTopic = () => {
    const referrerPath = readInternalReferrerPath();
    if (TOPICS_BY_PATH[referrerPath]) {
      return { ...TOPICS_BY_PATH[referrerPath], source: 'referrer' };
    }

    const attribution = readAttribution();
    const landing = attribution?.landing || '';
    if (TOPICS_BY_PATH[landing]) {
      return { ...TOPICS_BY_PATH[landing], source: 'first-touch' };
    }

    return null;
  };

  const applyTopicContext = () => {
    if (activeTopic) return activeTopic;

    const topic = resolveTopic();
    if (!topic) return null;

    activeTopic = topic;
    form.dataset.callbackTopic = topic.key;
    form.dataset.callbackTopicSource = topic.source;

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
      topicSource: topic?.source || 'general',
      page: location.pathname,
      attribution: { ...getEventAttribution() }
    };
    window.dispatchEvent(new CustomEvent('parket36:callback-open', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_open',
        page: detail.page,
        trigger: detail.trigger,
        callback_topic: detail.topic,
        callback_topic_source: detail.topicSource,
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
      topic: topic?.key || 'general',
      topicSource: topic?.source || 'general'
    };
    window.dispatchEvent(new CustomEvent('parket36:callback-request', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_request',
        page: detail.page || location.pathname,
        service: detail.service || 'Обратный звонок по паркетным работам',
        callback_topic: detail.topic,
        callback_topic_source: detail.topicSource,
        attribution: detail.attribution || getEventAttribution()
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
