(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const LEAD_TIMEOUT_MS = 12_000;
  const LEAD_MAX_ATTEMPTS = 2;
  const RETRY_DELAY_MS = 650;
  const SUBMISSION_STATE_TIMEOUT_MS = (LEAD_TIMEOUT_MS * LEAD_MAX_ATTEMPTS) + RETRY_DELAY_MS + 5_000;
  const LEAD_FIELD_LIMITS = Object.freeze({
    'request-location': 160,
    'request-area': 80,
    'request-task': 3000,
    'request-callback': 160,
    'request-contact': 240
  });
  const LEAD_FIELD_LABELS = Object.freeze({
    service: 'Услуга',
    location: 'Район или населённый пункт',
    area: 'Площадь или объём',
    photos: 'Информация о фотографиях',
    video: 'Информация о видео',
    task: 'Описание задачи',
    callback_time: 'Удобное время связи',
    contact: 'Имя и телефон',
    page: 'Адрес страницы',
    utm_source: 'Источник перехода',
    utm_medium: 'Канал перехода',
    utm_campaign: 'Название кампании',
    utm_content: 'Содержание кампании',
    utm_term: 'Поисковый запрос'
  });
  const LEAD_FIELD_SELECTORS = Object.freeze({
    service: '#request-service',
    location: '#request-location',
    area: '#request-area',
    photos: '#request-photos',
    video: '#request-video',
    task: '#request-task',
    callback_time: '#request-callback',
    contact: '#request-contact'
  });
  const originalFetch = window.fetch.bind(window);

  const sleep = delay => new Promise(resolve => window.setTimeout(resolve, delay));

  const requestUrl = input => {
    if (typeof input === 'string') return input;
    if (input instanceof URL) return input.href;
    return input?.url || '';
  };

  const isLeadRequest = input => requestUrl(input).includes(LEAD_ENDPOINT_PATH);

  const leadErrorMessage = detail => {
    const code = detail?.code || 'lead_submit_failed';
    if (code === 'field_too_long') {
      const label = LEAD_FIELD_LABELS[detail?.field] || 'Одно из полей';
      const limit = Number(detail?.limit) || 0;
      return limit
        ? `Поле «${label}» слишком длинное. Сократите его до ${limit} символов.`
        : `Поле «${label}» слишком длинное. Сократите текст.`;
    }
    if (code === 'rate_limited') {
      return 'Слишком много попыток отправки. Подождите 15 минут или позвоните Ивану.';
    }
    if (code === 'task_or_contact_required') {
      return 'Проверьте описание задачи и контактные данные.';
    }
    if (code === 'origin_not_allowed') {
      return 'Форма открыта с неподдерживаемого адреса. Перейдите на parket36.ru или позвоните Ивану.';
    }
    if (code === 'ip_hash_salt_required' || code === 'server_not_configured') {
      return 'Сервис заявок временно не настроен. Позвоните Ивану или отправьте текст вручную.';
    }
    if (code === 'network_error') {
      return 'Не удалось связаться с сервисом заявок.';
    }
    return 'Автоматически отправить заявку не удалось.';
  };

  const readLeadError = async response => {
    let payload = {};
    try {
      payload = await response.clone().json();
    } catch {
      payload = {};
    }

    if (response.ok && payload?.ok !== false) return null;

    return {
      status: response.status,
      code: String(payload?.error || `lead_submit_${response.status}`),
      field: String(payload?.field || ''),
      limit: Number(payload?.limit) || 0,
      received: Number(payload?.received) || 0,
      requestId: String(payload?.request_id || '')
    };
  };

  const dispatchLeadError = detail => {
    window.dispatchEvent(new CustomEvent('parket36:lead-error', { detail }));
  };

  const addHoneypotFields = form => {
    ['website', 'company'].forEach(name => {
      if (form.elements.namedItem(name)) return;

      const wrapper = document.createElement('div');
      wrapper.hidden = true;
      wrapper.setAttribute('aria-hidden', 'true');

      const input = document.createElement('input');
      input.type = 'text';
      input.name = name;
      input.autocomplete = 'off';
      input.tabIndex = -1;
      input.setAttribute('data-lead-honeypot', name);

      wrapper.appendChild(input);
      form.prepend(wrapper);
    });
  };

  const setupLeadFieldLimits = form => {
    Object.entries(LEAD_FIELD_LIMITS).forEach(([id, maxLength]) => {
      const field = form.querySelector(`#${id}`);
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) return;
      field.maxLength = maxLength;
    });

    const taskField = form.querySelector('#request-task');
    if (!(taskField instanceof HTMLTextAreaElement)) return;

    let counter = form.querySelector('[data-lead-character-counter="request-task"]');
    if (!counter) {
      counter = document.createElement('span');
      counter.id = 'request-task-counter';
      counter.className = 'form-help';
      counter.dataset.leadCharacterCounter = 'request-task';
      taskField.insertAdjacentElement('afterend', counter);
    }

    const describedBy = new Set((taskField.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
    describedBy.add(counter.id);
    taskField.setAttribute('aria-describedby', Array.from(describedBy).join(' '));

    const updateCounter = () => {
      const used = taskField.value.length;
      counter.textContent = `${used} / ${LEAD_FIELD_LIMITS['request-task']}`;
      counter.setAttribute('aria-label', `Использовано ${used} из ${LEAD_FIELD_LIMITS['request-task']} символов`);
    };

    taskField.addEventListener('input', updateCounter);
    updateCounter();
  };

  const setupLeadFormState = form => {
    const status = form.querySelector('#request-status');
    const submitButton = form.querySelector('button[type="submit"]');
    let submissionInFlight = false;
    let submissionStateTimeout = 0;
    let invalidAnnouncementTimer = 0;
    let lastLeadError = null;

    if (status) {
      status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite');
      status.setAttribute('aria-atomic', 'true');
    }
    form.setAttribute('aria-busy', 'false');

    const clearSubmissionState = () => {
      submissionInFlight = false;
      form.setAttribute('aria-busy', 'false');
      if (submissionStateTimeout) {
        window.clearTimeout(submissionStateTimeout);
        submissionStateTimeout = 0;
      }
    };

    const announceFirstInvalidField = () => {
      invalidAnnouncementTimer = 0;
      if (!status) return;
      const firstInvalid = form.querySelector('input:invalid, textarea:invalid, select:invalid');
      status.textContent = firstInvalid?.id === 'request-contact'
        ? 'Укажите имя и телефон, чтобы Иван мог связаться с вами.'
        : 'Заполните обязательное поле перед отправкой заявки.';
    };

    window.addEventListener('parket36:lead-error', event => {
      lastLeadError = event.detail || null;
      if (lastLeadError?.code !== 'field_too_long') return;
      const selector = LEAD_FIELD_SELECTORS[lastLeadError.field];
      const field = selector ? form.querySelector(selector) : null;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;
      field.setAttribute('aria-invalid', 'true');
      field.focus();
    });

    if (status && typeof MutationObserver === 'function') {
      const feedbackObserver = new MutationObserver(() => {
        if (!lastLeadError) return;
        const current = status.textContent || '';
        let suffix = '';
        if (current.startsWith('Автоматически отправить заявку не удалось.')) {
          suffix = ' Текст скопирован: отправьте его Ивану вместе с фото или позвоните.';
        } else if (current.startsWith('Скопируйте готовый текст ниже')) {
          suffix = ' Скопируйте готовый текст ниже и отправьте его Ивану вместе с фотографиями пола.';
        } else {
          return;
        }

        const detail = lastLeadError;
        lastLeadError = null;
        status.textContent = `${leadErrorMessage(detail)}${suffix}`;
      });
      feedbackObserver.observe(status, { childList: true, characterData: true, subtree: true });
    }

    form.addEventListener('invalid', event => {
      const field = event.target;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;

      field.setAttribute('aria-invalid', 'true');
      if (!invalidAnnouncementTimer) {
        invalidAnnouncementTimer = window.setTimeout(announceFirstInvalidField, 0);
      }
    }, true);

    form.addEventListener('input', event => {
      const field = event.target;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;
      if (field.validity.valid) field.removeAttribute('aria-invalid');
    });

    form.addEventListener('change', event => {
      const field = event.target;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;
      if (field.validity.valid) field.removeAttribute('aria-invalid');
    });

    form.addEventListener('submit', event => {
      if (submissionInFlight) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (status) status.textContent = 'Заявка уже отправляется. Дождитесь результата.';
        return;
      }

      lastLeadError = null;
      submissionInFlight = true;
      form.setAttribute('aria-busy', 'true');
      submissionStateTimeout = window.setTimeout(clearSubmissionState, SUBMISSION_STATE_TIMEOUT_MS);
    }, true);

    if (submitButton && typeof MutationObserver === 'function') {
      const observer = new MutationObserver(() => {
        if (!submitButton.disabled && submissionInFlight) clearSubmissionState();
      });
      observer.observe(submitButton, { attributes: true, attributeFilter: ['disabled'] });
    }
  };

  document.querySelectorAll('#request-form').forEach(form => {
    addHoneypotFields(form);
    setupLeadFieldLimits(form);
    setupLeadFormState(form);
  });

  const bodyWithHoneypot = body => {
    if (typeof body !== 'string') return body;

    try {
      const payload = JSON.parse(body);
      const form = document.getElementById('request-form');
      payload.website = form?.elements.namedItem('website')?.value || '';
      payload.company = form?.elements.namedItem('company')?.value || '';
      return JSON.stringify(payload);
    } catch {
      return body;
    }
  };

  const fetchLeadAttempt = async (input, init) => {
    if (typeof AbortController !== 'function') {
      return originalFetch(input, init);
    }

    const controller = new AbortController();
    const abortFromCaller = () => controller.abort();
    const callerSignal = init.signal;

    if (callerSignal) {
      if (callerSignal.aborted) controller.abort();
      else callerSignal.addEventListener('abort', abortFromCaller, { once: true });
    }

    const timeoutId = window.setTimeout(() => controller.abort(), LEAD_TIMEOUT_MS);

    try {
      return await originalFetch(input, { ...init, signal: controller.signal });
    } finally {
      window.clearTimeout(timeoutId);
      callerSignal?.removeEventListener?.('abort', abortFromCaller);
    }
  };

  window.fetch = async (input, init = {}) => {
    if (!isLeadRequest(input)) return originalFetch(input, init);

    const leadInit = {
      ...init,
      body: bodyWithHoneypot(init.body)
    };

    let lastError = new Error('lead_submit_failed');

    for (let attempt = 1; attempt <= LEAD_MAX_ATTEMPTS; attempt += 1) {
      try {
        const response = await fetchLeadAttempt(input, leadInit);
        if (response.status < 500 || attempt === LEAD_MAX_ATTEMPTS) {
          const detail = await readLeadError(response);
          if (detail) dispatchLeadError(detail);
          return response;
        }
        lastError = new Error(`lead_submit_${response.status}`);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('lead_submit_failed');
        if (attempt === LEAD_MAX_ATTEMPTS) break;
      }

      await sleep(RETRY_DELAY_MS);
    }

    dispatchLeadError({ status: 0, code: 'network_error', field: '', limit: 0, received: 0, requestId: '' });
    throw lastError;
  };
})();