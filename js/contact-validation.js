(() => {
  const MIN_PHONE_DIGITS = 10;
  const MAX_PHONE_DIGITS = 15;
  const ERROR_MESSAGE = 'Укажите телефон для обратного звонка: не менее 10 цифр.';

  const phoneDigitCount = value => (String(value || '').match(/\d/g) || []).length;
  const hasCallbackPhone = value => {
    const count = phoneDigitCount(value);
    return count >= MIN_PHONE_DIGITS && count <= MAX_PHONE_DIGITS;
  };

  document.querySelectorAll('#request-form').forEach(form => {
    const field = form.querySelector('#request-contact');
    const status = form.querySelector('#request-status');
    if (!(field instanceof HTMLInputElement)) return;

    let serverPhoneErrorPending = false;

    const firstInvalidField = () => form.querySelector('input:invalid, textarea:invalid, select:invalid');
    const showPhoneError = () => {
      field.setAttribute('aria-invalid', 'true');
      if (status) status.textContent = ERROR_MESSAGE;
    };

    field.setAttribute('autocomplete', 'tel');
    field.setAttribute('inputmode', 'tel');
    field.addEventListener('input', () => {
      serverPhoneErrorPending = false;
      if (!hasCallbackPhone(field.value)) return;
      field.setCustomValidity('');
      field.removeAttribute('aria-invalid');
    });
    field.addEventListener('invalid', () => {
      if (hasCallbackPhone(field.value)) return;
      window.setTimeout(() => {
        if (firstInvalidField() === field) showPhoneError();
      }, 0);
    });

    window.addEventListener('parket36:lead-error', event => {
      if (event.detail?.code !== 'contact_phone_invalid') return;
      serverPhoneErrorPending = true;
      field.setCustomValidity(ERROR_MESSAGE);
      field.setAttribute('aria-invalid', 'true');
      field.focus();
      if (status) status.textContent = ERROR_MESSAGE;
    });

    if (status && typeof MutationObserver === 'function') {
      const serverErrorObserver = new MutationObserver(() => {
        if (!serverPhoneErrorPending) return;
        const current = status.textContent || '';
        if (current === ERROR_MESSAGE) return;
        if (!current.startsWith('Автоматически отправить заявку не удалось.') &&
            !current.startsWith('Скопируйте готовый текст ниже')) return;

        serverPhoneErrorPending = false;
        status.textContent = `${ERROR_MESSAGE} Проверьте номер и отправьте заявку ещё раз.`;
      });
      serverErrorObserver.observe(status, { childList: true, characterData: true, subtree: true });
    }

    form.addEventListener('submit', event => {
      const firstInvalid = firstInvalidField();
      if (firstInvalid && firstInvalid !== field) return;

      if (hasCallbackPhone(field.value)) {
        field.setCustomValidity('');
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
      field.setCustomValidity(ERROR_MESSAGE);
      field.focus();
      showPhoneError();
    }, true);
  });
})();
