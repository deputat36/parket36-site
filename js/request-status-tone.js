(() => {
  const form = document.getElementById('request-form');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!(status instanceof HTMLElement)) return;

  const VALID_TONES = new Set(['info', 'success', 'warning', 'error']);
  const PHONE_DISPLAY = '8 (900) 926-79-29';

  const assessmentWarningText = (delivery, fallbackVisible) => {
    const duplicate = Boolean(delivery?.duplicate);
    const notification = String(delivery?.notification || 'unknown');
    const subject = duplicate ? 'Заявка уже была сохранена' : 'Заявка сохранена';
    const deliveryText = duplicate && notification === 'unknown'
      ? 'повторная отправка не подтверждает автоматическое уведомление Ивану'
      : notification === 'disabled'
      ? 'автоматическое уведомление Ивану пока не настроено'
      : notification === 'partial_failure'
      ? 'доставку уведомления Ивану подтвердить не удалось'
      : 'автоматическое уведомление Ивану не подтверждено';
    const copyAction = fallbackVisible
      ? `${duplicate ? 'Скопируйте готовый текст ниже ещё раз' : 'Скопируйте готовый текст ниже'}, приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`
      : `${duplicate ? 'Текст снова скопирован' : 'Текст скопирован'} — приложите фотографии и позвоните Ивану по номеру ${PHONE_DISPLAY}.`;

    return `${subject}, но ${deliveryText}. ${copyAction}`;
  };

  const installAssessmentStatusGuard = () => {
    if (form.dataset.formKind === 'callback') return;

    const descriptor = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
    if (!descriptor?.get || !descriptor?.set) return;

    Object.defineProperty(status, 'textContent', {
      configurable: true,
      get() {
        return descriptor.get.call(this);
      },
      set(value) {
        let next = value == null ? '' : String(value);
        const delivery = window.parket36LastLeadDelivery;

        if (
          next.startsWith('Заявка отправлена Ивану') &&
          delivery &&
          delivery.notification !== 'sent'
        ) {
          next = assessmentWarningText(
            delivery,
            Boolean(form.querySelector('[data-request-fallback]'))
          );
        }

        descriptor.set.call(this, next);
      }
    });
  };

  const setTone = tone => {
    if (!VALID_TONES.has(tone)) {
      status.removeAttribute('data-status-tone');
      return;
    }
    status.dataset.statusTone = tone;
  };

  const classifyText = value => {
    const text = String(value || '').trim();
    if (!text) return '';

    if (
      text.startsWith('Опишите,') ||
      text.startsWith('Укажите,') ||
      text.startsWith('Укажите телефон') ||
      text.startsWith('Автоматически отправить заявку не удалось') ||
      text.startsWith('Скопируйте готовый текст ниже') ||
      text.includes('не менее 10 цифр')
    ) return 'error';

    if (
      text.includes('уже была сохранена') ||
      text.includes('уже был сохранён') ||
      text.includes('уведомление Ивану') ||
      text.includes('доставку уведомления') ||
      text.includes('повторная отправка не подтверждает')
    ) return 'warning';

    if (
      text.startsWith('Заявка отправлена Ивану') ||
      text.startsWith('Заявка на обратный звонок отправлена Ивану')
    ) return 'success';

    return 'info';
  };

  const syncToneFromText = () => {
    const tone = classifyText(status.textContent);
    if (tone) setTone(tone);
    else status.removeAttribute('data-status-tone');
  };

  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.setAttribute('aria-atomic', 'true');
  installAssessmentStatusGuard();

  if (typeof MutationObserver === 'function') {
    const observer = new MutationObserver(syncToneFromText);
    observer.observe(status, { childList: true, characterData: true, subtree: true });
  }

  window.addEventListener('parket36:lead', event => {
    const detail = event.detail;
    if (!detail) return;

    if (detail.type === 'request-copy') {
      setTone('error');
      return;
    }

    if (detail.type !== 'request-submit') return;
    setTone(detail.notification === 'sent' ? 'success' : 'warning');
  });

  syncToneFromText();
})();