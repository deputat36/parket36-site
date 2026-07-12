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

    const showPhoneError = () => {
      field.setAttribute('aria-invalid', 'true');
      if (status) status.textContent = ERROR_MESSAGE;
    };

    field.setAttribute('autocomplete', 'tel');
    field.setAttribute('inputmode', 'tel');
    field.addEventListener('input', () => {
      if (!hasCallbackPhone(field.value)) return;
      field.setCustomValidity('');
      field.removeAttribute('aria-invalid');
    });
    field.addEventListener('invalid', () => {
      if (hasCallbackPhone(field.value)) return;
      window.setTimeout(showPhoneError, 0);
    });

    form.addEventListener('submit', event => {
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
