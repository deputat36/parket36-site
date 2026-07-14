(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const KNOWN_NOTIFICATION_STATES = new Set(['sent', 'disabled', 'partial_failure']);
  const PHONE_DISPLAY = '8 (900) 926-79-29';
  const originalFetch = window.fetch.bind(window);
  let lastDelivery = null;

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

  window.fetch = async (input, init = {}) => {
    const response = await originalFetch(input, init);
    if (!requestUrl(input).includes(LEAD_ENDPOINT_PATH)) return response;

    lastDelivery = await readDelivery(response);
    return response;
  };

  document.addEventListener('submit', event => {
    if (event.target?.id === 'request-form') lastDelivery = null;
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
      ? 'Скопируйте готовый текст ниже, приложите фотографии и позвоните Ивану.'
      : 'Текст скопирован — приложите фотографии и позвоните Ивану.';
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
    if (!detail || detail.type !== 'request-submit') return;

    const form = document.getElementById('request-form');
    const status = form?.querySelector('#request-status');
    const callback = form?.dataset.formKind === 'callback';
    const fallbackVisible = Boolean(form?.querySelector('[data-request-fallback]'));

    if (status && !detail.duplicate && detail.notification !== 'sent') {
      status.textContent = warningText(detail.notification, callback, fallbackVisible);
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
