module.exports = {
  ci: {
    collect: {
      staticDistDir: './_site',
      url: [
        'http://localhost/',
        'http://localhost/zayavka/',
        'http://localhost/uslugi/ciklevka-parketa/',
        'http://localhost/sovety/pochemu-skripit-parket/',
        'http://localhost/sovety/',
        'http://localhost/sovety/skolko-sohnet-lak-na-parkete/',
        'http://localhost/sovety/pochemu-lak-na-parkete-shelushitsya-posle-lakirovki/'
      ],
      numberOfRuns: 3,
      settings: {
        chromeFlags: '--headless --no-sandbox --disable-dev-shm-usage'
      }
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.80, aggregationMethod: 'median' }],
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
