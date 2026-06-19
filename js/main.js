(() => {
  const ATTRIBUTION_KEY = 'parket36_attribution';

  const safeSessionGet = key => {
    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const safeSessionSet = (key, value) => {
    try {
      sessionStorage.setItem(key, value);
    } catch {
      // The site remains fully functional when browser storage is unavailable.
    }
  };

  const referrerHost = (() => {
    if (!document.referrer) return '';
    try {
      return new URL(document.referrer).hostname;
    } catch {
      return '';
    }
  })();

  const createAttribution = () => {
    const params = new URLSearchParams(location.search);
    const stored = safeSessionGet(ATTRIBUTION_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        // Ignore damaged session data and create a new attribution record.
      }
    }

    const attribution = {
      source: params.get('utm_source') || referrerHost || 'direct',
      medium: params.get('utm_medium') || '',
      campaign: params.get('utm_campaign') || '',
      content: params.get('utm_content') || '',
      term: params.get('utm_term') || '',
      landing: location.pathname,
      firstSeen: new Date().toISOString()
    };

    safeSessionSet(ATTRIBUTION_KEY, JSON.stringify(attribution));
    return attribution;
  };

  const attribution = createAttribution();
  window.parket36Attribution = Object.freeze({ ...attribution });

  const ensureStylesheet = href => {
    if (document.querySelector(`link[href="${href}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  };

  ensureStylesheet('/css/enhancements.css');
  ensureStylesheet('/css/photo-brief.css');
  ensureStylesheet('/css/interface-polish.css');
  ensureStylesheet('/css/mobile-menu.css');

  if (!document.querySelector('link[rel="manifest"]')) {
    const manifest = document.createElement('link');
    manifest.rel = 'manifest';
    manifest.href = '/manifest.webmanifest';
    document.head.appendChild(manifest);
  }

  document.querySelectorAll('.side-card > img[src*="/img/"]').forEach(img => {
    const card = img.closest('.side-card');
    if (!card) return;
    card.classList.add('side-card--photo-plan');
    card.dataset.photoSlot = img.getAttribute('alt') || 'Место для реального фото объекта';
    img.dataset.placeholderImage = 'true';
    img.setAttribute('aria-hidden', 'true');
  });

  document.querySelectorAll('.services-grid').forEach(grid => {
    const icons = Array.from(grid.querySelectorAll('.service-card__icon'));
    icons.forEach((icon, index) => {
      const value = (icon.textContent || '').trim();
      if (/^[0-9A-Za-zА-Яа-я]{1,3}$/.test(value)) return;
      icon.textContent = String(index + 1).padStart(2, '0');
      icon.setAttribute('aria-hidden', 'true');
      icon.title = 'Номер карточки';
    });
  });

  const main = document.querySelector('main');
  if (main) {
    main.id = main.id || 'main-content';
    if (!document.querySelector('.skip-link')) {
      const skipLink = document.createElement('a');
      skipLink.className = 'skip-link';
      skipLink.href = `#${main.id}`;
      skipLink.textContent = 'Перейти к содержанию';
      document.body.prepend(skipLink);
    }
  }

  const normalizePath = value => {
    if (!value) return '/';
    const path = value.split('#')[0].split('?')[0] || '/';
    if (path === '/') return '/';
    return path.endsWith('/') ? path : `${path}/`;
  };

  const toggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-nav]');

  if (nav) {
    const currentPath = normalizePath(location.pathname);
    nav.querySelectorAll('a').forEach(link => {
      let linkPath;
      try {
        linkPath = normalizePath(new URL(link.getAttribute('href') || '/', location.origin).pathname);
      } catch {
        return;
      }

      if (linkPath === currentPath || (linkPath !== '/' && currentPath.startsWith(linkPath))) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      }
    });
  }

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

  const backToTop = document.createElement('button');
  backToTop.type = 'button';
  backToTop.className = 'back-to-top';
  backToTop.textContent = '↑';
  backToTop.setAttribute('aria-label', 'Вернуться к началу страницы');
  document.body.appendChild(backToTop);

  const setBackToTopVisibility = () => {
    backToTop.classList.toggle('is-visible', window.scrollY > 650);
  };

  let backToTopTicking = false;
  window.addEventListener('scroll', () => {
    if (backToTopTicking) return;
    backToTopTicking = true;
    requestAnimationFrame(() => {
      setBackToTopVisibility();
      backToTopTicking = false;
    });
  }, { passive: true });

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  setBackToTopVisibility();

  const emitLead = detail => {
    const payload = {
      ...detail,
      page: location.pathname,
      attribution: { ...attribution }
    };

    window.dispatchEvent(new CustomEvent('parket36:lead', { detail: payload }));

    if (typeof window.ym === 'function') {
      const counterId = window.parket36MetrikaId;
      if (counterId) {
        try {
          window.ym(counterId, 'reachGoal', detail.type, payload);
        } catch {
          // Analytics must never break the public site.
        }
      }
    }
  };

  document.querySelectorAll('a[href^="tel:"]').forEach(link => {
    link.addEventListener('click', () => emitLead({
      type: 'phone',
      href: link.getAttribute('href')
    }));
  });

  document.querySelectorAll('a[href$="#request"], a[href="/#request"], a[href="#request"]').forEach(link => {
    link.addEventListener('click', () => emitLead({
      type: 'request-open',
      href: link.getAttribute('href')
    }));
  });

  const form = document.getElementById('request-form');
  if (form) {
    const status = document.getElementById('request-status');
    const serviceField = document.getElementById('request-service');
    const taskField = document.getElementById('request-task');

    if (status) {
      status.setAttribute('role', 'status');
    }

    document.querySelectorAll('[data-request-template]').forEach(button => {
      button.addEventListener('click', () => {
        const template = button.dataset.requestTemplate || '';
        const service = button.dataset.requestService || '';

        if (serviceField && service) {
          const option = Array.from(serviceField.options).find(item => item.value === service || item.textContent === service);
          if (option) serviceField.value = option.value;
        }

        if (taskField && template) {
          taskField.value = taskField.value.trim()
            ? `${taskField.value.trim()}\n\n${template}`
            : template;
          taskField.focus();
          taskField.setSelectionRange(taskField.value.length, taskField.value.length);
        }

        if (status) status.textContent = 'Шаблон добавлен. Уточните детали и скопируйте заявку.';
        emitLead({ type: 'request-template', service: service || 'не указана' });
      });
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();

      const service = serviceField?.value.trim() || 'не указана';
      const locationValue = document.getElementById('request-location')?.value.trim() || 'не указан';
      const task = taskField?.value.trim() || '';
      const contact = document.getElementById('request-contact')?.value.trim() || 'не указан';

      if (!task) {
        if (status) status.textContent = 'Опишите, что нужно сделать.';
        taskField?.focus();
        return;
      }

      const attributionLines = [
        `Источник: ${attribution.source}`,
        attribution.medium ? `Канал: ${attribution.medium}` : '',
        attribution.campaign ? `Кампания: ${attribution.campaign}` : '',
        `Страница входа: ${attribution.landing}`
      ].filter(Boolean);

      const text = [
        'Здравствуйте, Иван!',
        `Услуга: ${service}`,
        `Район/населённый пункт: ${locationValue}`,
        `Задача: ${task}`,
        `Контакт: ${contact}`,
        'Фотографии отправлю отдельными сообщениями: общий вид, проблемное место крупно, доступ к объекту и примерный объём.',
        '',
        ...attributionLines
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
          fallback.rows = 10;
          fallback.readOnly = true;
          fallback.setAttribute('aria-label', 'Готовый текст заявки');
          form.appendChild(fallback);
        }
        fallback.value = text;
        fallback.focus();
        fallback.select();
        if (status) status.textContent = 'Скопируйте готовый текст из поля ниже.';
      }

      emitLead({ type: 'request-copy', service });
    });
  }

  document.querySelectorAll('[data-current-year]').forEach(node => {
    node.textContent = String(new Date().getFullYear());
  });
})();
