(() => {
  const LEAD_ENDPOINT_PATH = '/functions/v1/parket-public-lead';
  const LEAD_TIMEOUT_MS = 12_000;
  const LEAD_MAX_ATTEMPTS = 2;
  const RETRY_DELAY_MS = 650;
  const originalFetch = window.fetch.bind(window);

  const sleep = delay => new Promise(resolve => window.setTimeout(resolve, delay));

  const requestUrl = input => {
    if (typeof input === 'string') return input;
    if (input instanceof URL) return input.href;
    return input?.url || '';
  };

  const isLeadRequest = input => requestUrl(input).includes(LEAD_ENDPOINT_PATH);

  const addHoneypotFields = form => {
    ['website', 'company'].forEach(name => {
      if (form.elements.namedItem(name)) return;

      const wrapper = document.createElement('div');
      wrapper.hidden = true;
      wrapper.setAttribute('aria-hidden', 'true');

      const input = document.createElement('input');
      input.type = 'text';
      input.name = name;
      input.autocomplete = 'off';
      input.tabIndex = -1;
      input.setAttribute('data-lead-honeypot', name);

      wrapper.appendChild(input);
      form.prepend(wrapper);
    });
  };

  document.querySelectorAll('#request-form').forEach(addHoneypotFields);

  const bodyWithHoneypot = body => {
    if (typeof body !== 'string') return body;

    try {
      const payload = JSON.parse(body);
      const form = document.getElementById('request-form');
      payload.website = form?.elements.namedItem('website')?.value || '';
      payload.company = form?.elements.namedItem('company')?.value || '';
      return JSON.stringify(payload);
    } catch {
      return body;
    }
  };

  const fetchLeadAttempt = async (input, init) => {
    if (typeof AbortController !== 'function') {
      return originalFetch(input, init);
    }

    const controller = new AbortController();
    const abortFromCaller = () => controller.abort();
    const callerSignal = init.signal;

    if (callerSignal) {
      if (callerSignal.aborted) controller.abort();
      else callerSignal.addEventListener('abort', abortFromCaller, { once: true });
    }

    const timeoutId = window.setTimeout(() => controller.abort(), LEAD_TIMEOUT_MS);

    try {
      return await originalFetch(input, { ...init, signal: controller.signal });
    } finally {
      window.clearTimeout(timeoutId);
      callerSignal?.removeEventListener?.('abort', abortFromCaller);
    }
  };

  window.fetch = async (input, init = {}) => {
    if (!isLeadRequest(input)) return originalFetch(input, init);

    const leadInit = {
      ...init,
      body: bodyWithHoneypot(init.body)
    };

    let lastError = new Error('lead_submit_failed');

    for (let attempt = 1; attempt <= LEAD_MAX_ATTEMPTS; attempt += 1) {
      try {
        const response = await fetchLeadAttempt(input, leadInit);
        if (response.status < 500 || attempt === LEAD_MAX_ATTEMPTS) return response;
        lastError = new Error(`lead_submit_${response.status}`);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('lead_submit_failed');
        if (attempt === LEAD_MAX_ATTEMPTS) break;
      }

      await sleep(RETRY_DELAY_MS);
    }

    throw lastError;
  };
})();
