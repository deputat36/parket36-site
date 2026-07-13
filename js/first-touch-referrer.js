(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const previousFetch = window.fetch.bind(window);

  const requestUrl = input => {
    if (typeof input === 'string') return input;
    if (input instanceof URL) return input.href;
    return input?.url || '';
  };

  const firstTouchReferrer = () => {
    const landing = window.parket36Attribution?.landing;
    if (typeof landing !== 'string' || !landing.startsWith('/')) return '';

    try {
      const url = new URL(landing, location.origin);
      if (url.origin !== location.origin) return '';
      url.search = '';
      url.hash = '';
      return url.href;
    } catch {
      return '';
    }
  };

  window.fetch = (input, init = {}) => {
    if (!requestUrl(input).includes(LEAD_ENDPOINT_PATH)) {
      return previousFetch(input, init);
    }

    const referrer = firstTouchReferrer();
    if (!referrer) return previousFetch(input, init);

    return previousFetch(input, {
      ...init,
      referrer,
      referrerPolicy: 'unsafe-url'
    });
  };
})();
