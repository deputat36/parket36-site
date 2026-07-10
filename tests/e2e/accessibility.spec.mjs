// accessibility.spec.mjs is validated by tools/check_workflows.py.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const pages = [
  { path: '/', name: 'главная страница' },
  { path: '/zayavka/', name: 'форма оценки' },
  { path: '/404.html', name: 'страница 404' }
];

const wcagTags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

function formatViolations(violations) {
  return violations.map(violation => {
    const targets = violation.nodes
      .flatMap(node => node.target)
      .slice(0, 8)
      .join(', ');
    return `${violation.id} [${violation.impact || 'unknown'}]: ${violation.help}\n${targets}`;
  }).join('\n\n');
}

for (const target of pages) {
  test(`axe: ${target.name} соответствует WCAG A/AA`, async ({ page }) => {
    await page.goto(target.path);

    const results = await new AxeBuilder({ page })
      .withTags(wcagTags)
      .analyze();

    expect(
      results.violations,
      `Обнаружены нарушения доступности на ${target.path}:\n\n${formatViolations(results.violations)}`
    ).toEqual([]);
  });
}
