/**
 * Visual Regression Tests
 * Captures and compares screenshots to detect unintended UI changes
 */
import { test, expect } from '@playwright/test';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');

    // Wait for dashboard to load completely
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });

    // Wait for any animations to complete
    await page.waitForTimeout(500);
  });

  test('full dashboard screenshot', async ({ page }) => {
    // Full page screenshot
    await expect(page).toHaveScreenshot('dashboard-full.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05  // Allow 5% difference for dynamic content
    });
  });

  test('dashboard header screenshot', async ({ page }) => {
    const header = page.locator('[data-testid="quick-stats"]');
    await expect(header).toHaveScreenshot('dashboard-header.png', {
      maxDiffPixelRatio: 0.1  // Metrics may change
    });
  });

  test('system resource bars screenshot', async ({ page }) => {
    const systemBar = page.locator('[data-testid="system-bar"]');
    await expect(systemBar).toHaveScreenshot('system-bar.png', {
      maxDiffPixelRatio: 0.15  // Resource percentages change
    });
  });

  test('service health matrix screenshot - Matrix layout', async ({ page }) => {
    // Ensure matrix layout is selected
    const matrixButton = page.locator('button', { hasText: 'Matrix' });
    await matrixButton.click();
    await page.waitForTimeout(300);

    const matrix = page.locator('[data-testid="service-health-matrix"]');
    await expect(matrix).toHaveScreenshot('service-matrix-matrix-layout.png', {
      maxDiffPixelRatio: 0.1  // Pulse animations may vary
    });
  });

  test('service health matrix screenshot - List layout', async ({ page }) => {
    // Switch to list layout
    const listButton = page.locator('button', { hasText: 'List' });
    await listButton.click();
    await page.waitForTimeout(300);

    // Screenshot the list view
    const dashboard = page.locator('[data-testid="dashboard"]');
    await expect(dashboard).toHaveScreenshot('dashboard-list-layout.png', {
      maxDiffPixelRatio: 0.1
    });
  });

  test('service health matrix screenshot - Hybrid layout', async ({ page }) => {
    // Switch to hybrid layout
    const hybridButton = page.locator('button', { hasText: 'Hybrid' });
    await hybridButton.click();
    await page.waitForTimeout(300);

    // Screenshot the hybrid view
    const dashboard = page.locator('[data-testid="dashboard"]');
    await expect(dashboard).toHaveScreenshot('dashboard-hybrid-layout.png', {
      maxDiffPixelRatio: 0.1
    });
  });

  test('LLM metrics panel screenshot - Grid layout', async ({ page }) => {
    // Ensure metrics are visible
    const metricsPanel = page.locator('[data-testid="llm-metrics"]');

    if (await metricsPanel.isVisible()) {
      await expect(metricsPanel).toHaveScreenshot('llm-metrics-grid.png', {
        maxDiffPixelRatio: 0.15  // Sparklines and trends may vary
      });
    } else {
      // Toggle metrics visible
      const toggleButton = page.locator('button', { hasText: /Show/ });
      if (await toggleButton.count() > 0) {
        await toggleButton.click();
        await page.waitForTimeout(300);
        await expect(metricsPanel).toHaveScreenshot('llm-metrics-grid.png', {
          maxDiffPixelRatio: 0.15
        });
      }
    }
  });

  test('single service cell screenshot', async ({ page }) => {
    const firstCell = page.locator('[data-testid="service-cell"]').first();

    if (await firstCell.count() > 0) {
      await expect(firstCell).toHaveScreenshot('service-cell.png', {
        maxDiffPixelRatio: 0.1  // Status indicators may pulse
      });
    }
  });

  test('metric pill screenshot', async ({ page }) => {
    const servicesMetric = page.locator('[data-testid="metric-pill-services"]');

    if (await servicesMetric.count() > 0) {
      await expect(servicesMetric).toHaveScreenshot('metric-pill-services.png', {
        maxDiffPixelRatio: 0.05
      });
    }
  });

  test('WebSocket indicator screenshot', async ({ page }) => {
    const wsIndicator = page.locator('[data-testid="ws-indicator"]');

    if (await wsIndicator.count() > 0) {
      await expect(wsIndicator).toHaveScreenshot('ws-indicator.png', {
        maxDiffPixelRatio: 0.1  // Pulse animation
      });
    }
  });
});

test.describe('Visual Regression - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('mobile dashboard screenshot', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    await page.waitForTimeout(500);

    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.1
    });
  });

  test('mobile service matrix screenshot', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="service-health-matrix"]', { timeout: 10000 });
    await page.waitForTimeout(500);

    const matrix = page.locator('[data-testid="service-health-matrix"]');
    await expect(matrix).toHaveScreenshot('service-matrix-mobile.png', {
      maxDiffPixelRatio: 0.1
    });
  });
});

test.describe('Visual Regression - Dark Mode', () => {
  test.skip(() => {
    // TODO: Implement dark mode toggle detection and testing
    // For now, skip these tests until dark mode is fully implemented
  });

  test('dark mode dashboard', async ({ page }) => {
    await page.goto('/');

    // Toggle dark mode (if available)
    const darkModeToggle = page.locator('[aria-label="Toggle dark mode"]');
    if (await darkModeToggle.count() > 0) {
      await darkModeToggle.click();
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('dashboard-dark-mode.png', {
        fullPage: true,
        maxDiffPixelRatio: 0.1
      });
    }
  });
});

test.describe('Visual Regression - Component States', () => {
  test('service cell hover state', async ({ page, isMobile }) => {
    if (isMobile) {
      test.skip(); // Hover doesn't work on mobile
    }

    await page.goto('/');
    await page.waitForSelector('[data-testid="service-cell"]', { timeout: 10000 });

    const firstCell = page.locator('[data-testid="service-cell"]').first();
    await firstCell.hover();
    await page.waitForTimeout(200);

    // Screenshot with tooltip visible
    await expect(page).toHaveScreenshot('service-cell-hover.png', {
      maxDiffPixelRatio: 0.1
    });
  });

  test('metric pill hover state', async ({ page, isMobile }) => {
    if (isMobile) {
      test.skip();
    }

    await page.goto('/');
    await page.waitForSelector('[data-testid="metric-pill-services"]', { timeout: 10000 });

    const servicesMetric = page.locator('[data-testid="metric-pill-services"]');
    await servicesMetric.hover();
    await page.waitForTimeout(200);

    await expect(servicesMetric).toHaveScreenshot('metric-pill-hover.png', {
      maxDiffPixelRatio: 0.1
    });
  });

  test('LLM metrics hidden state', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });

    // Find and click hide button
    const hideButton = page.locator('button', { hasText: /Hide/ });
    if (await hideButton.count() > 0) {
      await hideButton.click();
      await page.waitForTimeout(300);

      const dashboard = page.locator('[data-testid="dashboard"]');
      await expect(dashboard).toHaveScreenshot('dashboard-metrics-hidden.png', {
        maxDiffPixelRatio: 0.05
      });
    }
  });
});
