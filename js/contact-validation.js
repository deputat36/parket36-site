(() => {
  const MIN_PHONE_DIGITS = 10;
  const MAX_PHONE_DIGITS = 15;
  const ERROR_MESSAGE = 'Укажите телефон для обратного звонка: не менее 10 цифр.';

  const phoneDigitCount = value => (String(value || '').match(/\d/g) || []).length;

  document.querySelectorAll('#request-form').forEach(form => {
    const field = form.querySelector('#request-contact');
    const status = form.querySelector('#request-status');
    if (!(field instanceof HTMLInputElement)) return;

    const validate = () => {
      const count = phoneDigitCount(field.value);
      const valid = !field.value.trim() || (count >= MIN_PHONE_DIGITS && count <= MAX_PHONE_DIGITS);
      field.setCustomValidity(valid ? '' : ERROR_MESSAGE);
      if (valid) field.removeAttribute('aria-invalid');
      return valid;
    };

    field.setAttribute('autocomplete', 'tel');
    field.setAttribute('inputmode', 'tel');
    field.addEventListener('input', validate);
    field.addEventListener('blur', validate);

    form.addEventListener('submit', event => {
      if (validate() && field.value.trim()) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      field.setAttribute('aria-invalid', 'true');
      if (status) status.textContent = ERROR_MESSAGE;
      field.focus();
      field.reportValidity();
    }, true);
  });
})();
