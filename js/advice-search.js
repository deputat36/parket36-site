(() => {
  'use strict';

  const filter = document.querySelector('[data-advice-search]');
  if (!filter) return;

  const input = filter.querySelector('#advice-query');
  const reset = filter.querySelector('[data-advice-reset]');
  const results = filter.querySelector('#advice-results');
  if (!(input instanceof HTMLInputElement) || !reset || !results) return;

  const catalogs = Array.from(document.querySelectorAll('main section'))
    .filter(section => section.querySelector('.services-grid .service-card'))
    .map(section => ({
      section,
      articles: Array.from(section.querySelectorAll('.services-grid .service-card'))
        .map(card => ({
          card,
          text: (card.textContent || '').toLocaleLowerCase('ru-RU').replace(/ё/g, 'е')
        }))
    }));

  const total = catalogs.reduce((count, catalog) => count + catalog.articles.length, 0);
  if (!total) return;

  const wordForm = count => {
    const mod10 = count % 10;
    const mod100 = count % 100;
    return mod10 === 1 && mod100 !== 11 ? 'материал'
      : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? 'материала'
      : 'материалов';
  };

  const render = () => {
    const query = input.value.trim().toLocaleLowerCase('ru-RU').replace(/ё/g, 'е');
    const words = query.split(/\s+/).filter(Boolean);
    let visible = 0;

    for (const { section, articles } of catalogs) {
      let sectionVisible = 0;
      for (const { card, text } of articles) {
        const matches = words.every(word => text.includes(word));
        card.hidden = !matches;
        if (matches) {
          visible += 1;
          sectionVisible += 1;
        }
      }
      section.hidden = sectionVisible === 0;
    }

    reset.hidden = words.length === 0;
    results.textContent = words.length === 0
      ? `Все советы: ${total} ${wordForm(total)}.`
      : visible
        ? `Найдено: ${visible} ${wordForm(visible)}.`
        : 'Ничего не найдено. Попробуйте другое слово или позвоните Ивану.';
  };

  input.addEventListener('input', render);
  reset.addEventListener('click', () => {
    input.value = '';
    render();
    input.focus();
  });

  filter.hidden = false;
  render();
})();
