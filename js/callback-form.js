(() => {
  const form = document.querySelector('#request-form[data-form-kind="callback"]');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!status) return;

  let callbackOpenEmitted = false;

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

    const detail = {
      type: 'callback-open',
      href,
      trigger,
      page: location.pathname,
      attribution: { ...(window.parket36Attribution || {}) }
    };
    window.dispatchEvent(new CustomEvent('parket36:callback-open', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_open',
        page: detail.page,
        trigger: detail.trigger,
        attribution: detail.attribution
      });
    }

    sendGoal('callback-open', detail);
  };

  const emitCallbackRequest = leadDetail => {
    const detail = { ...leadDetail, type: 'callback-request' };
    window.dispatchEvent(new CustomEvent('parket36:callback-request', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_callback_request',
        page: detail.page || location.pathname,
        service: detail.service || 'Обратный звонок по паркетным работам',
        attribution: detail.attribution || window.parket36Attribution || {}
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
  window.setTimeout(emitHashEntry, 0);

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
