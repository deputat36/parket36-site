(() => {
  'use strict';

  const filter = document.querySelector('[data-advice-search]');
  if (!filter) return;

  const input = filter.querySelector('#advice-query');
  const reset = filter.querySelector('[data-advice-reset]');
  const results = filter.querySelector('#advice-results');
  const empty = filter.querySelector('[data-advice-empty]');
  const topics = filter.querySelector('[data-advice-topics]');
  if (!(input instanceof HTMLInputElement) || !reset || !results || !empty || !topics) return;

  const normalize = value => String(value).toLocaleLowerCase('ru-RU').normalize('NFKC').replace(/ё/g, 'е');
  const lexemes = [
    [/^(скрип|заскрип|поскрип)/, 'скрип'],
    [/^(щел|рассох|рассых)/, 'щель'],
    [/^(вода|воды|воде|водой|водою|воду|водя|водн|залив|залит|залил|затоп|протеч|протек|намок)/, 'вода'],
    [/^(циклев|отцикл|шлиф|отшлиф)/, 'шлифовка'],
    [/^(лак|лакир)/, 'лак'],
    [/^масл/, 'масло'],
    [/^(реставр|восстанов|ремонт)/, 'ремонт'],
    [/^(царап|поцарап|исцарап)/, 'царапина'],
    [/^скол(?:$|[ыаоуе]|ами|ах)/, 'скол'],
    [/^(потерт|износ|истер|потускн)/, 'износ'],
    [/^(сох|суш|высых|просох)/, 'сушка'],
    [/^мебел/, 'мебель'],
    [/^(цен|стоим|расцен|бюджет|прайс)/, 'стоимость'],
    [/^(ухаж|уход)/, 'уход'],
    [/^(мыть|мытье|мытья|моющ|уборк)/, 'уборка'],
    [/^паркет/, 'паркет'],
    [/^деревян/, 'дерево'],
    [/^пол(?:а|у|ом|е|ы|ов)?$/, 'пол']
  ];
  const wordsOf = value => (normalize(value).match(/[a-zа-я0-9]+/g) || [])
    .map(word => lexemes.find(([pattern]) => pattern.test(word))?.[1] || word);
  const stopWords = new Set([
    'и', 'или', 'как', 'что', 'делать', 'почему', 'когда', 'сколько', 'можно',
    'у', 'меня', 'мой', 'моя', 'мне', 'на', 'в', 'во', 'с', 'со', 'к', 'по',
    'о', 'об', 'для', 'ли', 'это', 'нужно', 'нужен', 'хочу', 'пожалуйста'
  ]);
  const generalWords = new Set(['паркет', 'пол', 'дерево']);
  const queryWords = value => {
    const normalized = normalize(value).replace(/сколько\s+стоит/g, 'стоимость');
    const meaningful = wordsOf(normalized).filter(word => !stopWords.has(word));
    const specific = meaningful.filter(word => !generalWords.has(word));
    return Array.from(new Set(specific.length ? specific : meaningful));
  };

  // Local catalogue vocabulary, never sent to a server or an analytics event.
  const aliases = {
    '/sovety/staryy-lak-na-parkete/': 'потёртости тусклый износ',
    '/sovety/ciklevka-ili-zamena-parketa/': 'потёртости износ',
    '/sovety/carapiny-na-parkete-chto-delat/': 'поцарапали царапины',
    '/sovety/kogda-mozhno-stavit-mebel-posle-lakirovki-parketa/': 'ставить мебель вернуть мебель',
    '/sovety/pochemu-lak-na-parkete-lipnet-posle-lakirovki/': 'лак не сохнет липкий'
  };
  const topicWords = {
    all: null,
    movement: ['скрип', 'щель', 'подвиж', 'планк', 'основан', 'отош'],
    damage: ['вода', 'пятн', 'вздул', 'царапина', 'скол', 'вмятин', 'животн'],
    sanding: ['шлифовка', 'ремонт', 'осмотр', 'подготов', 'краск', 'стоимость', 'износ'],
    finish: ['лак', 'масло', 'воск', 'тонир', 'блеск', 'матов', 'глянц', 'грунт'],
    care: ['сушка', 'уход', 'уборка', 'мебель', 'ковер', 'проветр', 'запах', 'ходить']
  };

  const catalogs = Array.from(document.querySelectorAll('main section'))
    .filter(section => section.querySelector('.services-grid .service-card'))
    .map(section => ({
      section,
      articles: Array.from(section.querySelectorAll('.services-grid .service-card'))
        .map(card => {
          const href = card.querySelector('a')?.getAttribute('href') || '';
          const title = card.querySelector('h3')?.textContent || '';
          const text = [title, card.querySelector('p')?.textContent, aliases[href]].filter(Boolean).join(' ');
          return { card, words: wordsOf(text), titleWords: wordsOf(title) };
        })
    }));

  const total = catalogs.reduce((count, catalog) => count + catalog.articles.length, 0);
  if (!total) return;

  const canonicalWords = new Set(lexemes.map(([, word]) => word));
  const matchesWord = (words, term) => canonicalWords.has(term)
    ? words.includes(term)
    : words.some(word => word.startsWith(term));
  const wordForm = count => {
    const mod10 = count % 10;
    const mod100 = count % 100;
    return mod10 === 1 && mod100 !== 11 ? 'материал'
      : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? 'материала'
      : 'материалов';
  };

  const historyKey = 'parket36AdviceSearch';
  const restoreSearch = () => {
    try {
      const saved = history.state?.[historyKey];
      if (!saved || typeof saved.query !== 'string') return;
      const radio = Array.from(topics.querySelectorAll('input')).find(item => item.value === saved.topic);
      if (!radio) return;
      input.value = saved.query.slice(0, input.maxLength);
      radio.checked = true;
    } catch {
      // Searching remains available when the browser restricts history access.
    }
  };
  const rememberSearch = () => {
    try {
      const current = history.state && typeof history.state === 'object' ? { ...history.state } : {};
      const topic = topics.querySelector('input:checked')?.value || 'all';
      if (input.value || topic !== 'all') current[historyKey] = { query: input.value, topic };
      else delete current[historyKey];
      // Keep Back/Forward useful without changing the address or using persistent app storage.
      history.replaceState(current, '');
    } catch {
      // Restricted history access must not stop searching or opening an article.
    }
  };
  let announcement;
  let saveTimer;
  const render = ({ deferAnnouncement = false } = {}) => {
    const query = input.value.trim();
    const words = queryWords(query);
    const selected = topics.querySelector('input:checked')?.value || 'all';
    const terms = topicWords[selected] || null;
    let visible = 0;

    for (const { section, articles } of catalogs) {
      let sectionVisible = 0;
      for (const { card, words: articleWords, titleWords } of articles) {
        const inTopic = !terms || terms.some(term => matchesWord(titleWords, term));
        const matches = inTopic && words.every(word => matchesWord(articleWords, word));
        card.hidden = !matches;
        if (matches) {
          visible += 1;
          sectionVisible += 1;
        }
      }
      section.hidden = sectionVisible === 0;
    }

    const active = query.length > 0 || selected !== 'all';
    reset.hidden = !active;
    empty.hidden = visible !== 0;
    const summary = !active
      ? `Все советы: ${total} ${wordForm(total)}.`
      : visible
        ? `Найдено: ${visible} ${wordForm(visible)}.`
        : 'Ничего не найдено. Сбросьте фильтр или попробуйте другое слово.';
    clearTimeout(announcement);
    if (deferAnnouncement) announcement = setTimeout(() => { results.textContent = summary; }, 180);
    else results.textContent = summary;
  };

  input.addEventListener('input', () => {
    render({ deferAnnouncement: true });
    clearTimeout(saveTimer);
    saveTimer = setTimeout(rememberSearch, 220);
  });
  input.addEventListener('change', rememberSearch);
  topics.addEventListener('change', () => {
    render();
    rememberSearch();
  });
  reset.addEventListener('click', () => {
    input.value = '';
    const all = topics.querySelector('input[value="all"]');
    if (all) all.checked = true;
    clearTimeout(saveTimer);
    rememberSearch();
    render();
    input.focus();
  });
  document.addEventListener('click', event => {
    if (event.target instanceof Element && event.target.closest('a[href]')) rememberSearch();
  });
  window.addEventListener('pagehide', () => {
    clearTimeout(saveTimer);
    rememberSearch();
  });
  window.addEventListener('pageshow', () => requestAnimationFrame(() => {
    restoreSearch();
    render();
  }));

  restoreSearch();
  filter.hidden = false;
  render();
})();
