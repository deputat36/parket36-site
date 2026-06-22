(() => {
  const root = document.documentElement;
  const storageKey = 'parket36-theme';
  const menuButton = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-nav]');
  const themeButtons = document.querySelectorAll('[data-theme-option]');
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  const setThemeMeta = theme => {
    if (!themeMeta) return;
    themeMeta.setAttribute('content', theme === 'dark' ? '#1f1712' : '#6f4628');
  };

  const applyTheme = theme => {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    setThemeMeta(theme);
    themeButtons.forEach(button => {
      const active = button.dataset.themeOption === theme;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  };

  const storedTheme = localStorage.getItem(storageKey);
  const preferredTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  applyTheme(storedTheme || preferredTheme);

  themeButtons.forEach(button => {
    button.addEventListener('click', () => {
      const theme = button.dataset.themeOption || 'light';
      localStorage.setItem(storageKey, theme);
      applyTheme(theme);
    });
  });

  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    nav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        nav.classList.remove('open');
        menuButton.setAttribute('aria-expanded', 'false');
      });
    });
  }

  const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
  const attribution = {
    source: new URLSearchParams(window.location.search).get('utm_source') || document.referrer || 'прямой заход',
    medium: new URLSearchParams(window.location.search).get('utm_medium') || '',
    campaign: new URLSearchParams(window.location.search).get('utm_campaign') || '',
    landing: window.location.pathname
  };

  const emitLead = detail => {
    window.dispatchEvent(new CustomEvent('parket36:lead', { detail: { ...detail, attribution } }));
  };

  phoneLinks.forEach(link => {
    link.addEventListener('click', () => emitLead({ type: 'phone-click', label: link.textContent.trim() }));
  });

  document.querySelectorAll('[data-copy-phone]').forEach(button => {
    button.addEventListener('click', async () => {
      const phone = button.dataset.copyPhone || '+79009267929';
      try {
        await navigator.clipboard.writeText(phone);
        button.textContent = 'Телефон скопирован';
        setTimeout(() => { button.textContent = 'Скопировать номер'; }, 1800);
        emitLead({ type: 'phone-copy' });
      } catch {
        button.textContent = phone;
      }
    });
  });

  document.querySelectorAll('[data-faq-question]').forEach(button => {
    const item = button.closest('.faq__item');
    const answer = item?.querySelector('.faq__answer');
    if (!item || !answer) return;
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', () => {
      const isOpen = item.classList.toggle('open');
      button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  });

  document.querySelectorAll('[data-filter]').forEach(group => {
    const buttons = group.querySelectorAll('button[data-filter-value]');
    const cards = document.querySelectorAll('[data-filter-card]');
    buttons.forEach(button => {
      button.addEventListener('click', () => {
        const value = button.dataset.filterValue || 'all';
        buttons.forEach(item => item.classList.toggle('active', item === button));
        cards.forEach(card => {
          const tags = (card.dataset.filterCard || '').split(',').map(item => item.trim());
          card.hidden = value !== 'all' && !tags.includes(value);
        });
      });
    });
  });

  document.querySelectorAll('[data-tabs]').forEach(tabs => {
    const buttons = tabs.querySelectorAll('[data-tab-target]');
    const panels = document.querySelectorAll('[data-tab-panel]');
    buttons.forEach(button => {
      button.addEventListener('click', () => {
        const target = button.dataset.tabTarget;
        buttons.forEach(item => item.classList.toggle('active', item === button));
        panels.forEach(panel => {
          panel.hidden = panel.dataset.tabPanel !== target;
        });
      });
    });
  });

  const costInputs = document.querySelectorAll('[data-cost-input]');
  const costOutput = document.querySelector('[data-cost-output]');
  const costNote = document.querySelector('[data-cost-note]');
  const formatRub = value => new Intl.NumberFormat('ru-RU').format(Math.round(value));

  const calcCost = () => {
    if (!costOutput || !costInputs.length) return;
    const area = Number(document.querySelector('[data-cost-input="area"]')?.value || 0);
    const service = document.querySelector('[data-cost-input="service"]')?.value || 'cycle';
    const finish = document.querySelector('[data-cost-input="finish"]')?.value || 'lacquer';
    const repair = document.querySelector('[data-cost-input="repair"]')?.checked;
    const furniture = document.querySelector('[data-cost-input="furniture"]')?.checked;

    const serviceBase = {
      cycle: 520,
      restore: 760,
      board: 480,
      install: 950,
      laminate: 420
    }[service] || 520;

    const finishBase = {
      lacquer: 260,
      oil: 310,
      wax: 280,
      none: 0
    }[finish] || 0;

    let total = area * (serviceBase + finishBase);
    if (repair) total += Math.max(area * 180, 2500);
    if (furniture) total += Math.max(area * 90, 1500);

    const minimum = service === 'laminate' ? 6000 : 9000;
    total = Math.max(total, area > 0 ? minimum : 0);

    costOutput.textContent = area > 0 ? `от ${formatRub(total)} ₽` : 'укажите площадь';
    if (costNote) {
      costNote.textContent = area > 0
        ? 'Это ориентир для первичного разговора. Итог зависит от состояния пола, материалов и доступа.'
        : 'Калькулятор не заменяет осмотр, но помогает понять порядок бюджета.';
    }
  };

  costInputs.forEach(input => input.addEventListener('input', calcCost));
  calcCost();

  document.querySelectorAll('[data-gallery]').forEach(gallery => {
    const main = gallery.querySelector('[data-gallery-main]');
    const buttons = gallery.querySelectorAll('[data-gallery-thumb]');
    buttons.forEach(button => {
      button.addEventListener('click', () => {
        if (!main) return;
        const src = button.dataset.galleryThumb;
        const alt = button.querySelector('img')?.alt || 'Пример работы';
        main.setAttribute('src', src);
        main.setAttribute('alt', alt);
        buttons.forEach(item => item.classList.toggle('active', item === button));
      });
    });
  });

  const compareSliders = document.querySelectorAll('[data-compare]');
  compareSliders.forEach(compare => {
    const range = compare.querySelector('input[type="range"]');
    const after = compare.querySelector('.compare__after');
    if (!range || !after) return;
    const update = () => {
      after.style.clipPath = `inset(0 ${100 - Number(range.value)}% 0 0)`;
    };
    range.addEventListener('input', update);
    update();
  });

  const checklist = document.querySelector('[data-checklist]');
  if (checklist) {
    const output = document.querySelector('[data-checklist-output]');
    const update = () => {
      const checked = checklist.querySelectorAll('input:checked').length;
      const total = checklist.querySelectorAll('input').length;
      if (output) output.textContent = `${checked} из ${total}`;
    };
    checklist.addEventListener('change', update);
    update();
  }

  const guideBuilder = document.querySelector('[data-guide-builder]');
  if (guideBuilder) {
    const output = document.querySelector('[data-guide-output]');
    const render = () => {
      const room = guideBuilder.querySelector('[name="room"]')?.value || 'комната';
      const condition = guideBuilder.querySelector('[name="condition"]')?.value || 'состояние пола';
      const goal = guideBuilder.querySelector('[name="goal"]')?.value || 'нужен совет';
      if (output) {
        output.textContent = `Здравствуйте, Иван. Нужно посмотреть ${room}. Сейчас: ${condition}. Хотим понять: ${goal}. Фото общего вида и проблемных мест приложу.`;
      }
    };
    guideBuilder.addEventListener('input', render);
    render();
  }

  const routeQuiz = document.querySelector('[data-route-quiz]');
  if (routeQuiz) {
    const result = document.querySelector('[data-route-result]');
    const answers = routeQuiz.querySelectorAll('input[type="radio"]');
    const routes = {
      dull: ['Циклёвка и новое покрытие', '/uslugi/ciklevka-parketa/'],
      gaps: ['Реставрация паркета', '/uslugi/restavraciya-parketa/'],
      board: ['Шлифовка дощатого пола', '/uslugi/shlifovka-doshchatogo-pola/'],
      new: ['Укладка паркета', '/uslugi/ukladka-parketa/'],
      finish: ['Подбор лака, масла или воска', '/uslugi/pokrytie-lakom-i-maslom/']
    };
    const update = () => {
      const checked = routeQuiz.querySelector('input[type="radio"]:checked');
      if (!checked || !result) return;
      const [label, href] = routes[checked.value] || routes.dull;
      result.innerHTML = `<strong>${label}</strong><span>Это предварительный маршрут. Иван уточнит состояние пола по фото или при осмотре.</span><a class="btn btn--primary" href="${href}">Открыть услугу</a>`;
    };
    answers.forEach(input => input.addEventListener('change', update));
    update();
  }

  const requestFlow = document.querySelector('[data-request-flow]');
  if (requestFlow) {
    const steps = Array.from(requestFlow.querySelectorAll('[data-request-step]'));
    const nextButtons = requestFlow.querySelectorAll('[data-request-next]');
    const prevButtons = requestFlow.querySelectorAll('[data-request-prev]');
    const counter = requestFlow.querySelector('[data-request-counter]');
    let current = 0;

    const showStep = index => {
      current = Math.max(0, Math.min(index, steps.length - 1));
      steps.forEach((step, stepIndex) => {
        step.hidden = stepIndex !== current;
      });
      if (counter) counter.textContent = `${current + 1} из ${steps.length}`;
    };

    nextButtons.forEach(button => button.addEventListener('click', () => showStep(current + 1)));
    prevButtons.forEach(button => button.addEventListener('click', () => showStep(current - 1)));
    showStep(0);
  }

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

    if (submitButton && submitButton.textContent.trim() === 'Скопировать заявку') {
      submitButton.textContent = 'Скопировать текст для оценки';
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

        if (status) status.textContent = 'Шаблон добавлен. Уточните детали и скопируйте текст для оценки.';
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
      const contact = contactField?.value.trim() || 'не указан';

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

      try {
        await navigator.clipboard.writeText(text);
        if (status) {
          status.textContent = 'Текст для оценки скопирован. Его можно вставить в сообщение или продиктовать по телефону.';
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
        if (status) status.textContent = 'Скопируйте готовый текст из поля ниже.';
      }

      emitLead({ type: 'request-copy', service, area, photos, video, callback: callback !== 'не указано' });
    });
  }

  document.querySelectorAll('[data-current-year]').forEach(node => {
    node.textContent = String(new Date().getFullYear());
  });
})();