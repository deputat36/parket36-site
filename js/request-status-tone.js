(() => {
  const form = document.getElementById('request-form');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!(status instanceof HTMLElement)) return;

  const VALID_TONES = new Set(['info', 'success', 'warning', 'error']);

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
