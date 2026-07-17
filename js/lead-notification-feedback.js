(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const KNOWN_NOTIFICATION_STATES = new Set(['sent', 'disabled', 'partial_failure']);
  const PHONE_DISPLAY = '8 (900) 926-79-29';
  const PHONE_HREF = 'tel:+79009267929';
  const ASSESSMENT_HREF = '/zayavka/';
  const originalFetch = window.fetch.bind(window);
  let lastDelivery = null;
  window.parket36LastLeadDelivery = null;

  const requestUrl = input => {
    if (typeof input === 'string') return input;
    if (input instanceof URL) return input.href;
    return input?.url || '';
  };

  const normalizeNotification = value => (
    KNOWN_NOTIFICATION_STATES.has(value) ? value : 'unknown'
  );

  const readDelivery = async response => {
    let payload = {};
    try {
      payload = await response.clone().json();
    } catch {
      payload = {};
    }

    if (!response.ok || payload?.ok === false) return null;
    return {
      requestId: String(payload?.request_id || ''),
      notification: normalizeNotification(payload?.notification),
      duplicate: Boolean(payload?.duplicate)
    };
  };

  const publishDelivery = delivery => {
    lastDelivery = delivery;
    window.parket36LastLeadDelivery = delivery ? Object.freeze({ ...delivery }) : null;
  };

  const readAttribution = () => ({ ...(window.parket36Attribution || {}) });

  const emitFallbackPhoneClick = (link, formKind) => {
    const payload = {
      href: link.getAttribute('href') || PHONE_HREF,
      page: location.pathname,
      attribution: readAttribution(),
      source: 'lead-fallback',
      formKind
    };

    window.dispatchEvent(new CustomEvent('parket36:phone-click', { detail: payload }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_phone_click',
        phone_href: payload.href,
        page: payload.page,
        attribution: payload.attribution,
        source: payload.source,
        form_kind: payload.formKind
      });
    }

    if (typeof window.ym === 'function' && window.parket36MetrikaId) {
      try {
        window.ym(window.parket36MetrikaId, 'reachGoal', 'phone-click', payload);
      } catch {
        // Analytics must never affect the fallback call action.
      }
    }
  };

  const emitAssessmentOpen = (link, formKind) => {
    const payload = {
      type: 'request-open',
      href: link.getAttribute('href') || ASSESSMENT_HREF,
      page: location.pathname,
      attribution: readAttribution(),
      source: 'lead-fallback',
      formKind
    };

    window.dispatchEvent(new CustomEvent('parket36:lead', { detail: payload }));

    if (typeof window.ym === 'function' && window.parket36MetrikaId) {
      try {
        window.ym(window.parket36MetrikaId, 'reachGoal', 'request-open', payload);
      } catch {
        // Analytics must never affect navigation to the full assessment form.
      }
    }
  };

  const clearFallbackActions = form => {
    form?.querySelector('[data-lead-fallback-actions]')?.remove();
  };

  const ensureFallbackActions = (form, callback) => {
    if (!form) return null;

    const existing = form.querySelector('[data-lead-fallback-actions]');
    if (existing) return existing;

    const formKind = callback ? 'callback' : 'assessment';
    const actions = document.createElement('div');
    actions.className = 'hero__actions lead-fallback-actions';
    actions.dataset.leadFallbackActions = 'true';
    actions.setAttribute('role', 'group');
    actions.setAttribute('aria-label', 'Быстрая связь с Иваном');

    const call = document.createElement('a');
    call.className = 'btn btn--primary';
    call.href = PHONE_HREF;
    call.textContent = 'Позвонить Ивану';
    call.addEventListener('click', () => emitFallbackPhoneClick(call, formKind));
    actions.appendChild(call);

    if (callback) {
      const assessment = document.createElement('a');
      assessment.className = 'btn btn--ghost';
      assessment.href = ASSESSMENT_HREF;
      assessment.textContent = 'Открыть оценку по фото';
      assessment.addEventListener('click', () => emitAssessmentOpen(assessment, formKind));
      actions.appendChild(assessment);
    }

    const status = form.querySelector('#request-status');
    if (status) status.insertAdjacentElement('afterend', actions);
    else form.appendChild(actions);

    return actions;
  };

  window.fetch = async (input, init = {}) => {
    const response = await originalFetch(input, init);
    if (!requestUrl(input).includes(LEAD_ENDPOINT_PATH)) return response;

    publishDelivery(await readDelivery(response));
    return response;
  };

  document.addEventListener('submit', event => {
    if (event.target?.id !== 'request-form') return;
    publishDelivery(null);
    clearFallbackActions(event.target);
  }, true);

  const warningText = (notification, callback, fallbackVisible) => {
    const subject = callback ? 'Номер сохранён' : 'Заявка сохранена';
    const delivery = notification === 'disabled'
      ? 'автоматическое уведомление Ивану пока не настроено'
      : notification === 'partial_failure'
      ? 'доставку уведомления Ивану подтвердить не удалось'
      : 'автоматическое уведомление Ивану не подтверждено';

    if (callback) {
      return `${subject}, но ${delivery}. Чтобы не ждать, позвоните Ивану по номеру ${PHONE_DISPLAY}.`;
    }

    const copyAction = fallbackVisible
      ? `Скопируйте готовый текст ниже, приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`
      : `Текст скопирован — приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`;
    return `${subject}, но ${delivery}. ${copyAction}`;
  };

  const enrichLeadEvent = event => {
    if (!event.detail || event.detail.type !== 'request-submit') return;
    const delivery = lastDelivery || {
      requestId: '',
      notification: 'unknown',
      duplicate: false
    };
    event.detail.notification = delivery.notification;
    event.detail.notificationConfirmed = delivery.notification === 'sent';
    event.detail.duplicate = delivery.duplicate;
    event.detail.requestId = delivery.requestId;
  };

  window.addEventListener('parket36:lead', enrichLeadEvent, true);

  window.addEventListener('parket36:lead', event => {
    const detail = event.detail;
    if (!detail || !['request-submit', 'request-copy'].includes(detail.type)) return;

    const form = document.getElementById('request-form');
    const status = form?.querySelector('#request-status');
    const callback = form?.dataset.formKind === 'callback';

    if (detail.type === 'request-copy') {
      ensureFallbackActions(form, callback);
      return;
    }

    const fallbackVisible = Boolean(form?.querySelector('[data-request-fallback]'));

    if (status && !detail.duplicate && detail.notification !== 'sent') {
      status.textContent = warningText(detail.notification, callback, fallbackVisible);
      ensureFallbackActions(form, callback);
    } else if (detail.notification === 'sent') {
      clearFallbackActions(form);
    }

    const notificationDetail = {
      notification: detail.notification,
      notificationConfirmed: detail.notificationConfirmed,
      duplicate: Boolean(detail.duplicate),
      requestId: detail.requestId || '',
      formKind: callback ? 'callback' : 'assessment',
      page: detail.page || location.pathname,
      service: detail.service || '',
      attribution: detail.attribution || window.parket36Attribution || {}
    };

    window.dispatchEvent(new CustomEvent('parket36:lead-notification', {
      detail: notificationDetail
    }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_lead_notification',
        notification_state: notificationDetail.notification,
        notification_confirmed: notificationDetail.notificationConfirmed,
        duplicate: notificationDetail.duplicate,
        form_kind: notificationDetail.formKind,
        page: notificationDetail.page,
        service: notificationDetail.service,
        attribution: notificationDetail.attribution
      });
    }

    if (typeof window.ym === 'function' && window.parket36MetrikaId) {
      try {
        window.ym(window.parket36MetrikaId, 'reachGoal', 'lead-notification', notificationDetail);
      } catch {
        // Notification analytics must never affect the public form.
      }
    }
  });
})();
