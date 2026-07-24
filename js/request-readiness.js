(() => {
  const form = document.getElementById('request-form');
  if (!(form instanceof HTMLFormElement)) return;

  const callback = form.dataset.formKind === 'callback';
  const submitButton = form.querySelector('button[type="submit"]');
  if (!(submitButton instanceof HTMLButtonElement)) return;

  const PHONE_DIGITS_MIN = 10;
  const PHONE_DIGITS_MAX = 15;
  const TASK_MIN_LENGTH = 35;

  const field = id => form.querySelector(`#${id}`);
  const value = id => String(field(id)?.value || '').trim();
  const phoneDigits = () => value('request-contact').replace(/\D/g, '');

  const criteria = callback
    ? [
        {
          key: 'location',
          label: 'район или населённый пункт',
          complete: () => value('request-location').length >= 2
        },
        {
          key: 'callback_time',
          label: 'удобное время для звонка',
          complete: () => value('request-callback').length >= 2
        },
        {
          key: 'contact',
          label: 'имя и корректный телефон',
          complete: () => {
            const digits = phoneDigits();
            return value('request-contact').length >= 3 && digits.length >= PHONE_DIGITS_MIN && digits.length <= PHONE_DIGITS_MAX;
          }
        }
      ]
    : [
        {
          key: 'location',
          label: 'район или населённый пункт',
          complete: () => value('request-location').length >= 2
        },
        {
          key: 'area',
          label: 'примерная площадь или объём',
          complete: () => value('request-area').length >= 1
        },
        {
          key: 'photos',
          label: 'хотя бы общий вид пола',
          complete: () => {
            const photos = value('request-photos');
            return Boolean(photos) && photos !== 'Фото ещё не сделал(а)';
          }
        },
        {
          key: 'task',
          label: 'описание состояния и желаемого результата',
          complete: () => value('request-task').length >= TASK_MIN_LENGTH
        },
        {
          key: 'contact',
          label: 'имя и корректный телефон',
          complete: () => {
            const digits = phoneDigits();
            return value('request-contact').length >= 3 && digits.length >= PHONE_DIGITS_MIN && digits.length <= PHONE_DIGITS_MAX;
          }
        }
      ];

  const panel = document.createElement('section');
  panel.className = 'request-readiness';
  panel.dataset.requestReadiness = 'true';
  panel.setAttribute('aria-label', callback ? 'Готовность заявки на обратный звонок' : 'Готовность заявки на оценку по фото');

  const headingRow = document.createElement('div');
  headingRow.className = 'request-readiness__heading';

  const title = document.createElement('strong');
  title.textContent = callback ? 'Готовность к обратному звонку' : 'Готовность обращения';

  const score = document.createElement('span');
  score.className = 'request-readiness__score';
  score.dataset.requestReadinessScore = 'true';

  headingRow.append(title, score);

  const progress = document.createElement('div');
  progress.className = 'request-readiness__progress';
  progress.setAttribute('role', 'progressbar');
  progress.setAttribute('aria-valuemin', '0');
  progress.setAttribute('aria-valuemax', String(criteria.length));
  progress.setAttribute('aria-label', 'Заполненность полезных данных');

  const progressBar = document.createElement('span');
  progressBar.className = 'request-readiness__progress-bar';
  progress.appendChild(progressBar);

  const summary = document.createElement('p');
  summary.className = 'request-readiness__summary';
  summary.setAttribute('aria-live', 'polite');
  summary.setAttribute('aria-atomic', 'true');

  const list = document.createElement('ul');
  list.className = 'request-readiness__list';

  const listItems = new Map();
  criteria.forEach(item => {
    const li = document.createElement('li');
    li.dataset.readinessKey = item.key;

    const mark = document.createElement('span');
    mark.className = 'request-readiness__mark';
    mark.setAttribute('aria-hidden', 'true');

    const text = document.createElement('span');
    text.textContent = item.label;

    li.append(mark, text);
    list.appendChild(li);
    listItems.set(item.key, { li, mark });
  });

  panel.append(headingRow, progress, summary, list);
  submitButton.insertAdjacentElement('beforebegin', panel);

  let lastSnapshot = '';

  const evaluate = () => {
    const states = criteria.map(item => ({ ...item, done: Boolean(item.complete()) }));
    const completed = states.filter(item => item.done).length;
    const missing = states.filter(item => !item.done);
    const ready = completed === criteria.length;

    score.textContent = `${completed} из ${criteria.length}`;
    progress.setAttribute('aria-valuenow', String(completed));
    progressBar.style.width = `${Math.round((completed / criteria.length) * 100)}%`;
    panel.classList.toggle('is-ready', ready);
    form.dataset.requestReadinessState = `${completed}/${criteria.length}`;

    states.forEach(item => {
      const nodes = listItems.get(item.key);
      if (!nodes) return;
      nodes.li.classList.toggle('is-complete', item.done);
      nodes.li.classList.toggle('is-missing', !item.done);
      nodes.mark.textContent = item.done ? '✓' : '○';
    });

    if (ready) {
      summary.textContent = callback
        ? 'Данных достаточно, чтобы Иван мог перезвонить без дополнительного уточнения контакта.'
        : 'Данных достаточно для первого ориентира. Фотографии и видео всё равно отправляются отдельными сообщениями.';
    } else {
      const firstMissing = missing.slice(0, 2).map(item => item.label).join(' и ');
      summary.textContent = callback
        ? `Можно отправить сейчас. Для более удобного звонка добавьте: ${firstMissing}.`
        : `Форму можно отправить сейчас. Для более полезного ответа добавьте: ${firstMissing}.`;
    }

    return {
      completed,
      total: criteria.length,
      ready,
      missing: missing.map(item => item.key)
    };
  };

  const update = () => {
    const snapshot = criteria.map(item => `${item.key}:${item.complete() ? 1 : 0}`).join('|');
    if (snapshot === lastSnapshot) return evaluate();
    lastSnapshot = snapshot;
    return evaluate();
  };

  const emitReadiness = state => {
    const detail = {
      type: 'request-readiness',
      formKind: callback ? 'callback' : 'assessment',
      completed: state.completed,
      total: state.total,
      ready: state.ready,
      missing: [...state.missing],
      page: location.pathname
    };

    window.dispatchEvent(new CustomEvent('parket36:request-readiness', { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({
        event: 'parket36_request_readiness',
        form_kind: detail.formKind,
        completed_count: detail.completed,
        total_count: detail.total,
        ready: detail.ready,
        missing_keys: detail.missing,
        page: detail.page
      });
    }

    if (typeof window.ym === 'function' && window.parket36MetrikaId) {
      try {
        window.ym(window.parket36MetrikaId, 'reachGoal', 'request-readiness', detail);
      } catch {
        // Analytics must never affect the request form.
      }
    }
  };

  form.addEventListener('input', update);
  form.addEventListener('change', update);
  form.addEventListener('submit', () => emitReadiness(update()), true);

  update();
})();
