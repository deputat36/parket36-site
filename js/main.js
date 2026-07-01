(() => {
  const ATTRIBUTION_KEY = 'parket36_attribution';
  const PARKET_LEAD_ENDPOINT = 'https://ofewxuqfjhamgerwzull.supabase.co/functions/v1/parket-public-lead';

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

  const createRequestId = () => {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `parket36-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  };

  const submitParketLead = async payload => {
    if (typeof fetch !== 'function') throw new Error('fetch_unavailable');

    const response = await fetch(PARKET_LEAD_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    });

    let result = {};
    try {
      result = await response.json();
    } catch {
      // A non-JSON response is treated as a temporary delivery failure.
    }

    if (!response.ok || (result && result.ok === false)) {
      throw new Error(result?.error || `lead_submit_${response.status}`);
    }

    return result;
  };

  const prefersReducedMotion = () => {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      return false;
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
  ensureStylesheet('/css/typography-polish.css');
  ensureStylesheet('/css/scroll-progress.css');
  ensureStylesheet('/css/accessibility-polish.css');
  ensureStylesheet('/css/cta-polish.css');
  ensureStylesheet('/css/logo-brand.css');

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

  const scrollProgress = document.createElement('div');
  scrollProgress.className = 'scroll-progress';
  scrollProgress.setAttribute('aria-hidden', 'true');

  const scrollProgressBar = document.createElement('span');
  scrollProgressBar.className = 'scroll-progress__bar';
  scrollProgress.appendChild(scrollProgressBar);
  document.body.appendChild(scrollProgress);

  const updateScrollProgress = () => {
    const scrollable = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const progress = Math.min(100, Math.max(0, (window.scrollY / scrollable) * 100));
    scrollProgressBar.style.width = `${progress}%`;
  };

  const backToTop = document.createElement('button');
  backToTop.type = 'button';
  backToTop.className = 'back-to-top';
  backToTop.textContent = '↑';
  backToTop.setAttribute('aria-label', 'Вернуться к началу страницы');
  document.body.appendChild(backToTop);

  const setBackToTopVisibility = () => {
    backToTop.classList.toggle('is-visible', window.scrollY > 650);
  };

  let scrollTicking = false;
  const updateScrollUi = () => {
    updateScrollProgress();
    setBackToTopVisibility();
  };

  window.addEventListener('scroll', () => {
    if (scrollTicking) return;
    scrollTicking = true;
    requestAnimationFrame(() => {
      updateScrollUi();
      scrollTicking = false;
    });
  }, { passive: true });

  window.addEventListener('resize', () => {
    updateScrollUi();
  }, { passive: true });

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  });

  updateScrollUi();

  const isPhoneLead = detail => ['phone', 'phone-inline'].includes(detail.type);

  const emitPhoneClick = payload => {
    window.dispatchEvent(new CustomEvent('parket36:phone-click', { detail: payload }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_phone_click',
        phone_href: payload.href || '',
        page: payload.page,
        attribution: payload.attribution
      });
    }

    if (typeof window.ym === 'function') {
      const counterId = window.parket36MetrikaId;
      if (counterId) {
        try {
          window.ym(counterId, 'reachGoal', 'phone-click', payload);
        } catch {
          // Analytics must never break the public site.
        }
      }
    }
  };

  const emitLead = detail => {
    const payload = {
      ...detail,
      page: location.pathname,
      attribution: { ...attribution }
    };

    window.dispatchEvent(new CustomEvent('parket36:lead', { detail: payload }));

    if (isPhoneLead(detail)) {
      emitPhoneClick(payload);
    }

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

  document.querySelectorAll('a[href]').forEach(link => {
    let url;
    try {
      url = new URL(link.getAttribute('href') || '', location.origin);
    } catch {
      return;
    }

    const isRequestAnchor = url.hash === '#request';
    const isPhotoAssessmentPage = normalizePath(url.pathname) === '/zayavka/';

    if (!isRequestAnchor && !isPhotoAssessmentPage) return;

    link.addEventListener('click', () => emitLead({
      type: 'request-open',
      href: link.getAttribute('href')
    }));
  });

  const addInlineLead = () => {
    if (!main || document.getElementById('request-form') || document.querySelector('.inline-lead')) return;
    const currentPath = normalizePath(location.pathname);
    if (!['/uslugi/', '/sovety/', '/resheniya/', '/portfolio/'].some(prefix => currentPath.startsWith(prefix))) return;

    const section = document.createElement('section');
    section.className = 'inline-lead';

    const container = document.createElement('div');
    container.className = 'container';
    const card = document.createElement('div');
    card.className = 'inline-lead__card';
    const content = document.createElement('div');
    const label = document.createElement('p');
    label.className = 'eyebrow';
    label.textContent = 'Не уверены, с чего начать?';
    const title = document.createElement('h2');
    title.textContent = 'Начните с фотографий пола и короткого разговора';
    const text = document.createElement('p');
    text.textContent = 'Опишите состояние паркета, примерную площадь и приложите несколько фото. Иван подскажет, поможет ли ремонт, шлифовка или лучше рассмотреть другой вариант.';
    const actions = document.createElement('div');
    actions.className = 'inline-lead__actions';
    const phone = document.createElement('a');
    phone.className = 'btn btn--primary';
    phone.href = 'tel:+79009267929';
    phone.textContent = 'Позвонить Ивану';
    const request = document.createElement('a');
    request.className = 'btn btn--ghost';
    request.href = '/zayavka/';
    request.textContent = 'Оценить по фото';

    content.append(label, title, text);
    actions.append(phone, request);
    card.append(content, actions);
    container.appendChild(card);
    section.appendChild(container);

    const after = document.querySelector('.subhero') || main.firstElementChild;
    if (after) after.insertAdjacentElement('afterend', section);
    else main.prepend(section);

    phone.addEventListener('click', () => emitLead({ type: 'phone-inline', href: phone.href }));
    request.addEventListener('click', () => emitLead({ type: 'request-inline', href: request.href }));
  };

  addInlineLead();

  const form = document.getElementById('request-form');
  if (form) {
    const status = document.getElementById('request-status');
    const serviceField = document.getElementById('request-service');
    const locationField = document.getElementById('request-location');
    const areaField = document.getElementById('request-area');

    const insertAssessmentSelect = (afterField, id, labelText, options) => {
      if (document.getElementById(id)) return;
      const anchorLabel = afterField?.closest('label');
      if (!anchorLabel) return;

      const label = document.createElement('label');
      label.textContent = labelText;

      const select = document.createElement('select');
      select.id = id;
      options.forEach(optionText => {
        const option = document.createElement('option');
        option.textContent = optionText;
        select.appendChild(option);
      });

      label.appendChild(select);
      anchorLabel.insertAdjacentElement('afterend', label);
    };

    insertAssessmentSelect(areaField, 'request-photos', 'Какие фото уже готовы?', [
      'Фото ещё не сделал(а)',
      'Есть общий вид комнаты',
      'Есть общий вид и дефекты крупно',
      'Есть общий вид, дефекты и зоны у стен',
      'Фото готовы полностью по инструкции'
    ]);
    insertAssessmentSelect(document.getElementById('request-photos'), 'request-video', 'Есть видео скрипа или подвижности?', [
      'Видео нет',
      'Видео скрипа есть',
      'Видео подвижных планок есть',
      'Видео сделаю при необходимости'
    ]);

    const photosField = document.getElementById('request-photos');
    const videoField = document.getElementById('request-video');
    const taskField = document.getElementById('request-task');
    const callbackField = document.getElementById('request-callback');
    const contactField = document.getElementById('request-contact');
    const submitButton = form.querySelector('button[type="submit"]');
    const disclosure = Array.from(form.querySelectorAll('.form-help')).at(-1);

    if (submitButton && submitButton.textContent.trim() === 'Скопировать заявку') {
      submitButton.textContent = 'Скопировать текст для оценки';
    }

    if (disclosure && /сервер|сайт/.test(disclosure.textContent || '')) {
      disclosure.textContent = 'Заявка отправляется Ивану через защищённую форму. Готовый текст также копируется, чтобы вы могли отправить фото отдельными сообщениями.';
    }

    if (status) {
      status.setAttribute('role', 'status');
    }

    document.querySelectorAll('[data-request-template]').forEach(button => {
      button.addEventListener('click', () => {
        const template = button.datasetRequestTemplate || button.dataset.requestTemplate || '';
        const service = button.datasetRequestService || button.dataset.requestService || '';

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

        if (status) status.textContent = 'Шаблон добавлен. Уточните детали и отправьте заявку Ивану.';
        emitLead({ type: 'request-template', service: service || 'не указана' });
      });
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();

      const service = serviceField?.value.trim() || 'не указана';
      const locationValue = locationField?.value.trim() || 'не указан';
      const area = areaField?.value.trim() || 'не указана';
      const photos = photosField?.value.trim() || 'не указано';
      const video = videoField?.value.trim() || 'не указано';
      const task = taskField?.value.trim() || '';
      const callback = callbackField?.value.trim() || 'не указано';
      const contact = contactField?.value.trim() || '';

      if (!task) {
        if (status) status.textContent = 'Опишите, что нужно сделать.';
        taskField?.focus();
        return;
      }

      if (!contact) {
        if (status) status.textContent = 'Укажите имя и телефон, чтобы Иван мог связаться с вами.';
        contactField?.focus();
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
        `Площадь/объём: ${area}`,
        `Фото: ${photos}`,
        `Видео скрипа/подвижности: ${video}`,
        `Задача: ${task}`,
        `Когда удобно связаться: ${callback}`,
        `Контакт: ${contact}`,
        'Фотографии отправлю отдельными сообщениями: общий вид, проблемное место крупно, зоны у стен и порогов, доступ к объекту и примерный объём.',
        '',
        ...attributionLines
      ].join('\n');

      const leadPayload = {
        request_id: createRequestId(),
        service,
        location: locationValue,
        area,
        photos,
        video,
        task,
        callback_time: callback,
        contact,
        page: location.pathname,
        utm_source: attribution.source,
        utm_medium: attribution.medium,
        utm_campaign: attribution.campaign,
        utm_content: attribution.content,
        utm_term: attribution.term
      };

      let leadSaved = false;
      let leadDuplicate = false;
      const defaultButtonText = submitButton?.textContent || '';

      if (status) status.textContent = 'Отправляем заявку Ивану и готовим текст для копирования...';
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = 'Отправляем...';
      }

      try {
        const result = await submitParketLead(leadPayload);
        leadSaved = true;
        leadDuplicate = Boolean(result?.duplicate);
      } catch {
        leadSaved = false;
      }

      try {
        await navigator.clipboard.writeText(text);
        if (status) {
          if (leadSaved && leadDuplicate) {
            status.textContent = 'Эта заявка уже была сохранена. Текст снова скопирован для отправки фото.';
          } else if (leadSaved) {
            status.textContent = 'Заявка отправлена Ивану. Текст также скопирован — приложите к нему фотографии пола.';
          } else {
            status.textContent = 'Автоматически отправить заявку не удалось. Текст скопирован: отправьте его Ивану вместе с фото или позвоните.';
          }
        }
      } catch {
        let fallback = form.querySelector('[data-request-fallback]');
        if (!fallback) {
          fallback = document.createElement('textarea');
          fallback.dataset.requestFallback = 'true';
          fallback.rows = 10;
          fallback.readOnly = true;
          fallback.setAttribute('aria-label', 'Готовый текст для оценки');
          form.appendChild(fallback);
        }
        fallback.value = text;
        fallback.focus();
        fallback.select();
        if (status) {
          status.textContent = leadSaved
            ? 'Заявка отправлена Ивану. Скопируйте готовый текст ниже и приложите к нему фотографии пола.'
            : 'Скопируйте готовый текст ниже и отправьте его Ивану вместе с фотографиями пола.';
        }
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = defaultButtonText;
        }
      }

      emitLead({
        type: leadSaved ? 'request-submit' : 'request-copy',
        service,
        area,
        photos,
        video,
        callback: callback !== 'не указано',
        backend: leadSaved ? 'supabase' : 'clipboard-fallback'
      });
    });
  }

  document.querySelectorAll('[data-current-year]').forEach(node => {
    node.textContent = String(new Date().getFullYear());
  });
})();