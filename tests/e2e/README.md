# Oxide E2E Tests with Playwright

End-to-end testing suite for the Oxide LLM Orchestrator Web UI using Playwright.

## Overview

This test suite provides comprehensive E2E testing coverage for:
- **UltraCompactDashboard**: Layout switching, metrics display, responsiveness
- **ServiceHealthMatrix**: Service grid, provider categorization, health indicators
- **EnhancedLLMMetrics**: Sparkline charts, trend indicators, metric cards
- **Accessibility**: ARIA labels, keyboard navigation, color contrast

## Quick Start

### Prerequisites

```bash
# Install Playwright (from project root)
npm install

# Install browsers
npx playwright install chromium
```

### Running Tests

```bash
# Run all E2E tests (headless)
npm run test:e2e

# Run tests with UI mode (interactive)
npm run test:e2e:ui

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# Debug specific test
npm run test:e2e:debug

# View last test report
npm run test:e2e:report
```

## Test Structure

```
tests/e2e/
├── README.md                 # This file
├── smoke.spec.js            # Basic smoke tests
├── dashboard.spec.js        # Dashboard component tests
└── visual-regression.spec.js # Visual regression tests (TODO)
```

## Test Coverage

### Dashboard Tests (dashboard.spec.js)

**UltraCompactDashboard:**
- ✓ Dashboard header with metrics
- ✓ System resource bars (CPU, RAM, Disk)
- ✓ Layout switching (Matrix, List, Hybrid)
- ✓ LLM metrics visibility toggle
- ✓ Provider type breakdown (CLI/Local/Remote)
- ✓ Responsive mobile layout

**ServiceHealthMatrix:**
- ✓ Service grid display
- ✓ Service cells with status indicators
- ✓ Hover tooltips
- ✓ Provider color themes
- ✓ Pulse animations for healthy services

**EnhancedLLMMetrics:**
- ✓ All metric cards (Latency, Throughput, Cost, Success Rate)
- ✓ Sparkline charts
- ✓ Trend indicators
- ✓ Color coding by metric type

**Accessibility:**
- ✓ ARIA labels
- ✓ Keyboard navigation
- ✓ Color contrast requirements

### Smoke Tests (smoke.spec.js)

- ✓ Dashboard loads successfully
- ✓ Basic page structure exists

## Configuration

### Playwright Config (playwright.config.js)

- **Test Directory**: `./tests/e2e`
- **Timeout**: 30s per test
- **Retry**: 2 retries on CI
- **Browsers**: Chromium, Firefox, WebKit
- **Mobile**: Pixel 5, iPhone 12
- **Web Server**: Auto-starts Vite dev server on port 3000

### Environment Variables

```bash
# Run in CI mode (enables retries)
CI=true npm run test:e2e

# Custom base URL (default: http://localhost:3000)
PLAYWRIGHT_BASE_URL=http://localhost:3001 npm run test:e2e
```

## Writing Tests

### Test IDs

All components use `data-testid` attributes for stable selectors:

```javascript
// Dashboard
page.locator('[data-testid="dashboard"]')

// Quick stats
page.locator('[data-testid="metric-pill-services"]')
page.locator('[data-testid="metric-pill-active"]')

// System resources
page.locator('[data-testid="system-bar"]')
page.locator('[data-testid="cpu-bar"]')
page.locator('[data-testid="memory-bar"]')

// LLM metrics
page.locator('[data-testid="llm-metrics"]')
page.locator('[data-testid="metric-card"]')

// Service matrix
page.locator('[data-testid="service-health-matrix"]')
page.locator('[data-testid="service-cell"]')

// WebSocket
page.locator('[data-testid="ws-indicator"]')
```

### Example Test

```javascript
import { test, expect } from '@playwright/test';

test('should display service health matrix', async ({ page }) => {
  // Navigate to dashboard
  await page.goto('/');

  // Wait for component to load
  const matrix = page.locator('[data-testid="service-health-matrix"]');
  await expect(matrix).toBeVisible();

  // Check service cells exist
  const cells = page.locator('[data-testid="service-cell"]');
  const count = await cells.count();
  expect(count).toBeGreaterThan(0);

  // Verify first cell has status indicator
  const statusDot = cells.first().locator('.rounded-full.w-2.h-2');
  await expect(statusDot).toBeVisible();
});
```

## Visual Regression Testing

### Setup

```bash
# Generate baseline screenshots
npm run test:e2e -- --update-snapshots

# Compare against baseline
npm run test:e2e
```

### Configuration

Visual regression tests use Playwright's screenshot comparison:

```javascript
// Full page screenshot
await expect(page).toHaveScreenshot('dashboard.png');

// Component screenshot
const matrix = page.locator('[data-testid="service-health-matrix"]');
await expect(matrix).toHaveScreenshot('service-matrix.png');

// With threshold
await expect(page).toHaveScreenshot('dashboard.png', {
  maxDiffPixelRatio: 0.1  // Allow 10% difference
});
```

## Debugging Tests

### UI Mode (Recommended)

```bash
npm run test:e2e:ui
```

Features:
- Interactive test selection
- Step-by-step execution
- DOM snapshot navigation
- Network request inspection
- Console log viewing

### Debug Mode

```bash
npm run test:e2e:debug
```

Features:
- Pauses before each action
- Opens Playwright Inspector
- Allows step-through debugging

### Headed Mode

```bash
npm run test:e2e:headed
```

Shows browser window during test execution.

### Trace Viewer

If tests fail, traces are automatically captured:

```bash
npx playwright show-trace test-results/path/to/trace.zip
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: |
          npm ci
          cd src/oxide/web/frontend && npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Best Practices

1. **Use data-testid for selectors**: Avoid CSS classes that may change
2. **Wait for specific elements**: Use `waitForSelector` instead of arbitrary timeouts
3. **Test user flows, not implementation**: Focus on what users do
4. **Keep tests independent**: Each test should work in isolation
5. **Use fixtures for common setup**: Reduce code duplication
6. **Test across browsers**: Enable all browser projects for compatibility

## Troubleshooting

### Tests timeout

- Increase timeout in playwright.config.js
- Check if dev server is starting correctly
- Verify network requests aren't blocked

### Flaky tests

- Add explicit waits for dynamic content
- Use `waitForLoadState('networkidle')` for AJAX
- Increase `expect` timeout for slow operations

### Visual regression failures

- Check screenshot diffs in test results
- Update snapshots if intentional changes: `--update-snapshots`
- Adjust `maxDiffPixelRatio` for minor acceptable differences

### Can't find elements

- Verify component has correct `data-testid`
- Check element is visible (not `display: none`)
- Use Playwright Inspector to debug selectors

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Visual Comparisons](https://playwright.dev/docs/test-snapshots)

## Contributing

When adding new components:

1. Add `data-testid` attributes to interactive elements
2. Write E2E tests covering user interactions
3. Include accessibility tests (ARIA, keyboard nav)
4. Add visual regression tests for UI changes
5. Update this README with new test IDs

## License

MIT - Oxide Project
