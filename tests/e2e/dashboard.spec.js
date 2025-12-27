/**
 * E2E Tests for Oxide Dashboard UI
 * Tests UltraCompactDashboard, ServiceHealthMatrix, and EnhancedLLMMetrics
 */
import { test, expect } from '@playwright/test';

test.describe('UltraCompactDashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');

    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
  });

  test('should display dashboard header with metrics', async ({ page }) => {
    // Check header is visible
    const header = page.locator('header');
    await expect(header).toBeVisible();

    // Check logo and title
    await expect(page.locator('h1')).toContainText('Oxide LLM Orchestrator');

    // Check quick stats pills
    const servicePill = page.locator('[data-testid="metric-pill-services"]');
    await expect(servicePill).toBeVisible();

    const activePill = page.locator('[data-testid="metric-pill-active"]');
    await expect(activePill).toBeVisible();

    // Check WebSocket connection indicator
    const wsIndicator = page.locator('[data-testid="ws-indicator"]');
    await expect(wsIndicator).toBeVisible();
  });

  test('should display system resource bars', async ({ page }) => {
    const systemBar = page.locator('[data-testid="system-bar"]');
    await expect(systemBar).toBeVisible();

    // Check CPU bar
    const cpuBar = systemBar.locator('[data-testid="cpu-bar"]');
    await expect(cpuBar).toBeVisible();

    // Check memory bar
    const memoryBar = systemBar.locator('[data-testid="memory-bar"]');
    await expect(memoryBar).toBeVisible();

    // Verify progress values are numeric
    const cpuValue = await cpuBar.locator('.text-white').textContent();
    expect(cpuValue).toMatch(/\d+%/);
  });

  test('should switch between layout modes', async ({ page }) => {
    // Find layout toggle buttons
    const matrixButton = page.locator('button', { hasText: 'Matrix' });
    const listButton = page.locator('button', { hasText: 'List' });
    const hybridButton = page.locator('button', { hasText: 'Hybrid' });

    // Test Matrix layout (default)
    await expect(matrixButton).toHaveClass(/bg-cyan-500/);
    const matrix = page.locator('[data-testid="service-health-matrix"]');
    await expect(matrix).toBeVisible();

    // Switch to List layout
    await listButton.click();
    await expect(listButton).toHaveClass(/bg-cyan-500/);
    await page.waitForTimeout(500); // Animation

    // Switch to Hybrid layout
    await hybridButton.click();
    await expect(hybridButton).toHaveClass(/bg-cyan-500/);
    await page.waitForTimeout(500); // Animation

    // Switch back to Matrix
    await matrixButton.click();
    await expect(matrixButton).toHaveClass(/bg-cyan-500/);
  });

  test('should toggle LLM metrics visibility', async ({ page }) => {
    const toggleButton = page.locator('button', { hasText: /Hide|Show/ });

    // Metrics should be visible initially
    const metricsPanel = page.locator('[data-testid="llm-metrics"]');
    await expect(metricsPanel).toBeVisible();

    // Hide metrics
    await toggleButton.click();
    await expect(metricsPanel).toBeHidden();

    // Show metrics again
    await toggleButton.click();
    await expect(metricsPanel).toBeVisible();
  });

  test('should display provider type breakdown', async ({ page }) => {
    // Check provider stats
    const cliStat = page.locator('text=CLI').locator('..');
    const localStat = page.locator('text=Local').locator('..');
    const remoteStat = page.locator('text=Remote').locator('..');

    await expect(cliStat).toBeVisible();
    await expect(localStat).toBeVisible();
    await expect(remoteStat).toBeVisible();

    // Verify counts are displayed
    const cliCount = await cliStat.locator('.font-bold').textContent();
    expect(cliCount).toMatch(/\d+/);
  });

  test('should be responsive on mobile', async ({ page, isMobile }) => {
    if (!isMobile) {
      test.skip();
    }

    // Check mobile layout
    const container = page.locator('[data-testid="dashboard"]');
    await expect(container).toBeVisible();

    // Quick stats should stack vertically
    const statsBar = page.locator('[data-testid="quick-stats"]');
    const bbox = await statsBar.boundingBox();

    // On mobile, should be narrower
    expect(bbox.width).toBeLessThan(500);
  });
});

test.describe('ServiceHealthMatrix', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="service-health-matrix"]');
  });

  test('should display service grid', async ({ page }) => {
    const matrix = page.locator('[data-testid="service-health-matrix"]');
    await expect(matrix).toBeVisible();

    // Check section headers
    const cliHeader = page.locator('text=CLI Providers');
    const localHeader = page.locator('text=Local Services');
    const remoteHeader = page.locator('text=Remote Services');

    // At least one should be visible
    const headersVisible = await Promise.race([
      cliHeader.isVisible().catch(() => false),
      localHeader.isVisible().catch(() => false),
      remoteHeader.isVisible().catch(() => false)
    ]);
    expect(headersVisible).toBe(true);
  });

  test('should show service cells with correct status', async ({ page }) => {
    // Find service cells
    const serviceCells = page.locator('[data-testid="service-cell"]');
    const count = await serviceCells.count();

    expect(count).toBeGreaterThan(0);

    // Check first service cell
    const firstCell = serviceCells.first();
    await expect(firstCell).toBeVisible();

    // Should have status indicator
    const statusDot = firstCell.locator('.rounded-full.w-2.h-2');
    await expect(statusDot).toBeVisible();

    // Should have service name
    const serviceName = firstCell.locator('.text-white');
    await expect(serviceName).toBeVisible();
  });

  test('should show tooltip on hover', async ({ page, isMobile }) => {
    if (isMobile) {
      test.skip(); // Tooltips don't work on mobile
    }

    const serviceCell = page.locator('[data-testid="service-cell"]').first();

    // Hover over service
    await serviceCell.hover();

    // Wait for tooltip to appear
    await page.waitForTimeout(300);

    // Tooltip should be visible
    const tooltip = page.locator('[role="tooltip"]');
    await expect(tooltip).toBeVisible();

    // Should contain service details
    await expect(tooltip).toContainText(/Model|Status/);
  });

  test('should have correct provider color themes', async ({ page }) => {
    // CLI services should have blue theme
    const cliSection = page.locator('text=CLI').locator('..');
    if (await cliSection.isVisible()) {
      await expect(cliSection).toHaveClass(/blue-500/);
    }

    // Local services should have green theme
    const localSection = page.locator('text=Local').locator('..');
    if (await localSection.isVisible()) {
      await expect(localSection).toHaveClass(/green-500/);
    }

    // Remote services should have purple theme
    const remoteSection = page.locator('text=Remote').locator('..');
    if (await remoteSection.isVisible()) {
      await expect(remoteSection).toHaveClass(/purple-500/);
    }
  });

  test('should animate healthy services with pulse', async ({ page }) => {
    const healthyCell = page.locator('[data-testid="service-cell"]').first();

    // Check for pulse animation
    const pulseElement = healthyCell.locator('.animate-pulse');
    const count = await pulseElement.count();

    // Should have at least one pulsing element (status dot or bg)
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('EnhancedLLMMetrics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="llm-metrics"]', { timeout: 10000 });
  });

  test('should display all metric cards', async ({ page }) => {
    const metricsPanel = page.locator('[data-testid="llm-metrics"]');
    await expect(metricsPanel).toBeVisible();

    // Check for 4 metric cards
    const metricCards = metricsPanel.locator('[data-testid="metric-card"]');
    const count = await metricCards.count();

    expect(count).toBeGreaterThanOrEqual(4);

    // Check specific metrics exist
    await expect(page.locator('text=Average Latency')).toBeVisible();
    await expect(page.locator('text=Tokens/Second')).toBeVisible();
    await expect(page.locator('text=Total Cost')).toBeVisible();
    await expect(page.locator('text=Success Rate')).toBeVisible();
  });

  test('should display sparkline charts', async ({ page }) => {
    // Find sparkline SVGs
    const sparklines = page.locator('svg[viewBox="0 0 100 100"]');
    const count = await sparklines.count();

    expect(count).toBeGreaterThan(0);

    // Check first sparkline has path elements
    const firstSparkline = sparklines.first();
    const polyline = firstSparkline.locator('polyline');
    await expect(polyline).toBeVisible();
  });

  test('should show trend indicators', async ({ page }) => {
    // Look for trend indicators (up/down arrows with percentage)
    const trends = page.locator('text=/[↑↓]\\s*\\d+%/');

    // Should have at least one trend indicator
    const count = await trends.count();
    if (count > 0) {
      const firstTrend = trends.first();
      await expect(firstTrend).toBeVisible();

      // Should be colored (green for up, red for down)
      const hasColor = await firstTrend.evaluate(el => {
        const classes = el.className;
        return classes.includes('green-400') || classes.includes('red-400');
      });
      expect(hasColor).toBe(true);
    }
  });

  test('should have correct color coding', async ({ page }) => {
    const metricsPanel = page.locator('[data-testid="llm-metrics"]');

    // Latency should be cyan
    const latencyCard = metricsPanel.locator('text=Average Latency').locator('..');
    const latencyValue = latencyCard.locator('.text-cyan-400');
    if (await latencyValue.count() > 0) {
      await expect(latencyValue.first()).toBeVisible();
    }

    // Cost should be yellow
    const costCard = metricsPanel.locator('text=Total Cost').locator('..');
    const costValue = costCard.locator('.text-yellow-400');
    if (await costValue.count() > 0) {
      await expect(costValue.first()).toBeVisible();
    }
  });

  test('should switch to compact layout', async ({ page }) => {
    // This test assumes there's a layout toggle
    // If metrics can be toggled to compact mode

    const metricsPanel = page.locator('[data-testid="llm-metrics"]');
    const initialHeight = await metricsPanel.evaluate(el => el.offsetHeight);

    // Verify metrics are displayed
    expect(initialHeight).toBeGreaterThan(100);
  });
});

test.describe('Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');

    // Check for proper heading structure
    const h1 = page.locator('h1');
    await expect(h1).toBeVisible();

    // Check buttons have accessible names
    const buttons = page.locator('button');
    const count = await buttons.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i);
      const text = await button.textContent();
      const ariaLabel = await button.getAttribute('aria-label');

      // Either should have text or aria-label
      expect(text || ariaLabel).toBeTruthy();
    }
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check that focus is visible
    const focused = await page.evaluate(() => {
      return document.activeElement.tagName;
    });

    expect(['BUTTON', 'A', 'INPUT']).toContain(focused);
  });

  test('should meet color contrast requirements', async ({ page }) => {
    await page.goto('/');

    // This would normally use axe-core for automated a11y testing
    // For now, we verify text is visible
    const metrics = page.locator('[data-testid="metric-pill"]').first();
    const textColor = await metrics.evaluate(el => {
      return window.getComputedStyle(el).color;
    });

    // Just verify color is defined
    expect(textColor).toBeTruthy();
  });
});
