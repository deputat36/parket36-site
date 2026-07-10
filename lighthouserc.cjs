module.exports = {
  ci: {
    collect: {
      staticDistDir: './_site',
      url: [
        'http://localhost/',
        'http://localhost/zayavka/'
      ],
      numberOfRuns: 1,
      settings: {
        chromeFlags: '--headless --no-sandbox --disable-dev-shm-usage'
      }
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', { minScore: 0.65 }],
        'categories:accessibility': ['error', { minScore: 0.90 }],
        'categories:best-practices': ['warn', { minScore: 0.85 }],
        'categories:seo': ['error', { minScore: 0.90 }]
      }
    },
    upload: {
      target: 'filesystem',
      outputDir: './lighthouse-report'
    }
  }
};
