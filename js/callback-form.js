(() => {
  const form = document.querySelector('#request-form[data-form-kind="callback"]');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!status) return;

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

    if (typeof window.ym === 'function' && window.parket36MetrikaId) {
      try {
        window.ym(window.parket36MetrikaId, 'reachGoal', 'callback-request', detail);
      } catch {
        // Analytics must never affect the callback form.
      }
    }
  };

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
