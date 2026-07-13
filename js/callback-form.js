(() => {
  const form = document.querySelector('#request-form[data-form-kind="callback"]');
  if (!(form instanceof HTMLFormElement)) return;

  const status = form.querySelector('#request-status');
  if (!status) return;

  window.addEventListener('parket36:lead', event => {
    if (!event.detail || !['request-submit', 'request-copy'].includes(event.detail.type)) return;

    status.textContent = event.detail.type === 'request-submit'
      ? 'Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.'
      : 'Автоматически отправить заявку не удалось. Текст скопирован — позвоните Ивану или используйте полную форму оценки.';
  });
})();
