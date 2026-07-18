(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const KNOWN_NOTIFICATION_STATES = new Set(['sent', 'disabled', 'partial_failure']);
  const PHONE_DISPLAY = '8 (900) 926-79-29';
  const PHONE_HREF = 'tel:+79009267929';
  const ASSESSMENT_HREF = '/zayavka/';
  const MOBILE_CTA_CLEARANCE_PX = 16;
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

  const clearFallbackText = form => {
    form?.querySelector('[data-request-fallback]')?.remove();
  };

  const shouldMoveFallbackFocus = form => {
    if (!form) return false;
    const active = document.activeElement;
    if (!active || active === document.body || active === form) return true;
    if (active instanceof HTMLElement && active.matches('[data-request-fallback]')) return false;

    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector('#request-status');
    return active === submit || active === status;
  };

  const keepFallbackAboveMobileCta = actions => {
    window.requestAnimationFrame(() => {
      if (!actions.isConnected) return;

      const mobileCta = document.querySelector('.mobile-cta');
      if (!(mobileCta instanceof HTMLElement)) return;

      const style = window.getComputedStyle(mobileCta);
      if (style.display === 'none' || style.visibility === 'hidden') return;

      const actionsRect = actions.getBoundingClientRect();
      const ctaRect = mobileCta.getBoundingClientRect();
      const overlap = actionsRect.bottom - (ctaRect.top - MOBILE_CTA_CLEARANCE_PX);
      if (overlap <= 0) return;

      window.scrollBy({ top: overlap, left: 0, behavior: 'auto' });
    });
  };

  const focusFallbackActions = (actions, form) => {
    if (!(actions instanceof HTMLElement) || !shouldMoveFallbackFocus(form)) return;
    actions.focus({ preventScroll: true });
    actions.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
    keepFallbackAboveMobileCta(actions);
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
    actions.tabIndex = -1;

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
    if (status?.id) actions.setAttribute('aria-describedby', status.id);
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
    clearFallbackText(event.target);
  }, true);

  const warningText = (notification, callback, fallbackVisible, duplicate) => {
    const subject = duplicate
      ? callback ? 'Номер уже был сохранён' : 'Заявка уже была сохранена'
      : callback ? 'Номер сохранён' : 'Заявка сохранена';
    const delivery = duplicate && notification === 'unknown'
      ? 'повторная отправка не подтверждает автоматическое уведомление Ивану'
      : notification === 'disabled'
      ? 'автоматическое уведомление Ивану пока не настроено'
      : notification === 'partial_failure'
      ? 'доставку уведомления Ивану подтвердить не удалось'
      : 'автоматическое уведомление Ивану не подтверждено';

    if (callback) {
      return `${subject}, но ${delivery}. Чтобы не ждать, позвоните Ивану по номеру ${PHONE_DISPLAY}.`;
    }

    const copyAction = fallbackVisible
      ? `${duplicate ? 'Скопируйте готовый текст ниже ещё раз' : 'Скопируйте готовый текст ниже'}, приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`
      : `${duplicate ? 'Текст снова скопирован' : 'Текст скопирован'} — приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`;
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
      const actions = ensureFallbackActions(form, callback);
      focusFallbackActions(actions, form);
      return;
    }

    const fallbackVisible = Boolean(form?.querySelector('[data-request-fallback]'));

    if (status && detail.notification !== 'sent') {
      status.textContent = warningText(
        detail.notification,
        callback,
        fallbackVisible,
        Boolean(detail.duplicate)
      );
      const actions = ensureFallbackActions(form, callback);
      focusFallbackActions(actions, form);
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