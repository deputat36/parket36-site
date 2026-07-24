(() => {
  const form = document.getElementById('request-form');
  if (!(form instanceof HTMLFormElement)) return;

  const submitButton = form.querySelector('[data-form-safety-submit="true"]');
  const status = form.querySelector('#request-status');
  if (!(submitButton instanceof HTMLButtonElement) || !(status instanceof HTMLElement)) return;

  const PHONE_HREF = 'tel:+79009267929';
  const PHONE_DISPLAY = '8 (900) 926-79-29';
  let submitAttempt = 0;

  const clearSafetyFallback = () => {
    form.querySelector('[data-form-safety-actions]')?.remove();
  };

  const ensureSafetyFallback = () => {
    const existing = form.querySelector('[data-form-safety-actions]');
    if (existing instanceof HTMLElement) return existing;

    const actions = document.createElement('div');
    actions.className = 'hero__actions lead-fallback-actions';
    actions.dataset.formSafetyActions = 'true';
    actions.setAttribute('role', 'group');
    actions.setAttribute('aria-label', 'Резервная связь с Иваном');
    actions.tabIndex = -1;

    const phone = document.createElement('a');
    phone.className = 'btn btn--primary';
    phone.href = PHONE_HREF;
    phone.textContent = 'Позвонить Ивану';
    actions.appendChild(phone);

    const assessment = document.createElement('a');
    assessment.className = 'btn btn--ghost';
    assessment.href = '/zayavka/';
    assessment.textContent = form.dataset.formKind === 'callback'
      ? 'Открыть оценку по фото'
      : 'Обновить страницу формы';
    if (form.dataset.formKind !== 'callback') {
      assessment.href = location.pathname + location.search + '#request';
    }
    actions.appendChild(assessment);

    status.insertAdjacentElement('afterend', actions);
    return actions;
  };

  const releaseSubmissionState = () => {
    form.removeAttribute('aria-busy');
    submitButton.disabled = true;
    window.requestAnimationFrame(() => {
      submitButton.disabled = false;
    });
  };

  const showIncompleteLoad = () => {
    status.textContent = `Форма загрузилась не полностью. Данные не отправлены и остались в полях. Позвоните Ивану по номеру ${PHONE_DISPLAY} или обновите страницу.`;
    status.dataset.statusTone = 'error';
    releaseSubmissionState();
    const actions = ensureSafetyFallback();
    actions.focus({ preventScroll: true });
    actions.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  };

  form.addEventListener('submit', event => {
    event.preventDefault();
    clearSafetyFallback();

    const attempt = ++submitAttempt;
    const statusBefore = (status.textContent || '').trim();

    window.setTimeout(() => {
      if (attempt !== submitAttempt) return;
      const statusAfter = (status.textContent || '').trim();
      if (statusAfter && statusAfter !== statusBefore) return;
      showIncompleteLoad();
    }, 0);
  }, true);

  form.dataset.formSafety = 'active';
  submitButton.disabled = false;
  submitButton.removeAttribute('aria-disabled');
})();
