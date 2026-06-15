(() => {
  const toggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-nav]');

  const closeMenu = () => {
    if (!toggle || !nav) return;
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  };

  if (toggle && nav) {
    nav.id = nav.id || 'site-navigation';
    toggle.setAttribute('aria-controls', nav.id);
    toggle.setAttribute('aria-expanded', 'false');

    toggle.addEventListener('click', () => {
      const opened = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(opened));
    });

    nav.addEventListener('click', event => {
      if (event.target.closest('a')) closeMenu();
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeMenu();
    });
  }

  const emitLead = detail => {
    window.dispatchEvent(new CustomEvent('parket36:lead', { detail }));
  };

  document.querySelectorAll('a[href^="tel:"]').forEach(link => {
    link.addEventListener('click', () => emitLead({
      type: 'phone',
      href: link.getAttribute('href'),
      page: location.pathname
    }));
  });

  document.querySelectorAll('a[href*="max.ru"]').forEach(link => {
    link.addEventListener('click', () => emitLead({
      type: 'max',
      href: link.getAttribute('href'),
      page: location.pathname
    }));
  });

  const form = document.getElementById('request-form');
  if (form) {
    form.addEventListener('submit', async event => {
      event.preventDefault();

      const service = document.getElementById('request-service')?.value.trim() || 'не указана';
      const locationValue = document.getElementById('request-location')?.value.trim() || 'не указан';
      const taskField = document.getElementById('request-task');
      const task = taskField?.value.trim() || '';
      const contact = document.getElementById('request-contact')?.value.trim() || 'не указан';
      const status = document.getElementById('request-status');

      if (!task) {
        if (status) status.textContent = 'Опишите, что нужно сделать.';
        taskField?.focus();
        return;
      }

      const text = [
        'Здравствуйте, Иван!',
        `Услуга: ${service}`,
        `Район/населённый пункт: ${locationValue}`,
        `Задача: ${task}`,
        `Контакт: ${contact}`,
        'Фотографии отправлю отдельными сообщениями.'
      ].join('\n');

      try {
        await navigator.clipboard.writeText(text);
        if (status) {
          status.textContent = 'Заявка скопирована. Её можно вставить в сообщение или продиктовать по телефону.';
        }
      } catch {
        let fallback = form.querySelector('[data-request-fallback]');
        if (!fallback) {
          fallback = document.createElement('textarea');
          fallback.dataset.requestFallback = 'true';
          fallback.rows = 8;
          fallback.readOnly = true;
          fallback.setAttribute('aria-label', 'Готовый текст заявки');
          form.appendChild(fallback);
        }
        fallback.value = text;
        fallback.focus();
        fallback.select();
        if (status) status.textContent = 'Скопируйте готовый текст из поля ниже.';
      }

      emitLead({ type: 'request-copy', service, page: location.pathname });
    });
  }

  document.querySelectorAll('[data-current-year]').forEach(node => {
    node.textContent = String(new Date().getFullYear());
  });
})();
