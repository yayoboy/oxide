/**
 * Screenshot Generator for Documentation
 * Captures high-quality screenshots of UI components for README and docs
 */
import { test } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Screenshot output directory
const SCREENSHOT_DIR = './docs/screenshots';

test.beforeAll(async () => {
  // Create screenshots directory if it doesn't exist
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
});

test.describe('Documentation Screenshots', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    await page.waitForTimeout(1000); // Wait for animations
  });

  test('capture full dashboard overview', async ({ page }) => {
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '01-dashboard-overview.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('capture dashboard header with metrics', async ({ page }) => {
    const header = page.locator('[data-testid="quick-stats"]');
    await header.screenshot({
      path: path.join(SCREENSHOT_DIR, '02-dashboard-header.png'),
      animations: 'disabled'
    });
  });

  test('capture WebSocket indicator', async ({ page }) => {
    const wsIndicator = page.locator('[data-testid="ws-indicator"]');
    await wsIndicator.screenshot({
      path: path.join(SCREENSHOT_DIR, '03-websocket-indicator.png'),
      animations: 'disabled'
    });
  });

  test('capture system resource bars', async ({ page }) => {
    const systemBar = page.locator('[data-testid="system-bar"]');
    await systemBar.screenshot({
      path: path.join(SCREENSHOT_DIR, '04-system-resources.png'),
      animations: 'disabled'
    });
  });

  test('capture service health matrix - Matrix layout', async ({ page }) => {
    const matrixButton = page.locator('button', { hasText: 'Matrix' });
    await matrixButton.click();
    await page.waitForTimeout(500);

    const matrix = page.locator('[data-testid="service-health-matrix"]');
    await matrix.screenshot({
      path: path.join(SCREENSHOT_DIR, '05-service-matrix-layout.png'),
      animations: 'disabled'
    });
  });

  test('capture service health matrix - List layout', async ({ page }) => {
    const listButton = page.locator('button', { hasText: 'List' });
    await listButton.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '06-service-list-layout.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('capture service health matrix - Hybrid layout', async ({ page }) => {
    const hybridButton = page.locator('button', { hasText: 'Hybrid' });
    await hybridButton.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '07-service-hybrid-layout.png'),
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('capture LLM metrics panel - Grid layout', async ({ page }) => {
    const metricsPanel = page.locator('[data-testid="llm-metrics"]');

    if (await metricsPanel.isVisible()) {
      await metricsPanel.screenshot({
        path: path.join(SCREENSHOT_DIR, '08-llm-metrics-grid.png'),
        animations: 'disabled'
      });
    } else {
      console.log('LLM metrics panel not visible, skipping screenshot');
    }
  });

  test('capture individual metric cards', async ({ page }) => {
    const metricCards = page.locator('[data-testid="metric-card"]');
    const count = await metricCards.count();

    if (count > 0) {
      // Capture first metric card as example
      await metricCards.first().screenshot({
        path: path.join(SCREENSHOT_DIR, '09-metric-card-example.png'),
        animations: 'disabled'
      });
    }
  });

  test('capture single service cell', async ({ page }) => {
    const firstCell = page.locator('[data-testid="service-cell"]').first();

    if (await firstCell.count() > 0) {
      await firstCell.screenshot({
        path: path.join(SCREENSHOT_DIR, '10-service-cell.png'),
        animations: 'disabled'
      });
    }
  });

  test('capture provider breakdown stats', async ({ page }) => {
    // Find provider stats section (CLI/Local/Remote counts)
    const providerStats = page.locator('text=CLI').locator('..');

    if (await providerStats.count() > 0) {
      // Capture the parent container with all provider stats
      const statsContainer = providerStats.locator('..').first();
      await statsContainer.screenshot({
        path: path.join(SCREENSHOT_DIR, '11-provider-breakdown.png'),
        animations: 'disabled'
      });
    }
  });

  test('capture layout toggle controls', async ({ page }) => {
    const layoutToggle = page.locator('button', { hasText: 'Matrix' }).locator('..');

    if (await layoutToggle.count() > 0) {
      await layoutToggle.screenshot({
        path: path.join(SCREENSHOT_DIR, '12-layout-toggle.png'),
        animations: 'disabled'
      });
    }
  });

  test('capture mobile view', async ({ page, browser }) => {
    // Create mobile context
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 667 },
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
    });

    const mobilePage = await mobileContext.newPage();
    await mobilePage.goto('/');
    await mobilePage.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    await mobilePage.waitForTimeout(1000);

    await mobilePage.screenshot({
      path: path.join(SCREENSHOT_DIR, '13-mobile-dashboard.png'),
      fullPage: true,
      animations: 'disabled'
    });

    await mobileContext.close();
  });

  test('capture tablet view', async ({ page, browser }) => {
    // Create tablet context
    const tabletContext = await browser.newContext({
      viewport: { width: 768, height: 1024 },
      userAgent: 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)'
    });

    const tabletPage = await tabletContext.newPage();
    await tabletPage.goto('/');
    await tabletPage.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    await tabletPage.waitForTimeout(1000);

    await tabletPage.screenshot({
      path: path.join(SCREENSHOT_DIR, '14-tablet-dashboard.png'),
      fullPage: true,
      animations: 'disabled'
    });

    await tabletContext.close();
  });
});

test.describe('Component Detail Screenshots', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    await page.waitForTimeout(1000);
  });

  test('capture metric pill variants', async ({ page }) => {
    const pillDir = path.join(SCREENSHOT_DIR, 'metric-pills');
    if (!fs.existsSync(pillDir)) {
      fs.mkdirSync(pillDir, { recursive: true });
    }

    // Capture each metric pill individually
    const pills = [
      'metric-pill-services',
      'metric-pill-active',
      'metric-pill-total',
      'metric-pill-success',
      'metric-pill-avg-time'
    ];

    for (const pillId of pills) {
      const pill = page.locator(`[data-testid="${pillId}"]`);
      if (await pill.count() > 0) {
        await pill.screenshot({
          path: path.join(pillDir, `${pillId}.png`),
          animations: 'disabled'
        });
      }
    }
  });

  test('capture service cell with tooltip', async ({ page, isMobile }) => {
    if (isMobile) {
      test.skip(); // Tooltips don't work on mobile
    }

    const firstCell = page.locator('[data-testid="service-cell"]').first();

    if (await firstCell.count() > 0) {
      // Hover to show tooltip
      await firstCell.hover();
      await page.waitForTimeout(500);

      // Capture with tooltip visible
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, '15-service-cell-tooltip.png'),
        clip: await firstCell.boundingBox(),
        animations: 'disabled'
      });
    }
  });
});

test.afterAll(async () => {
  console.log(`\n✅ Screenshots generated in ${SCREENSHOT_DIR}\n`);
  console.log('Screenshot files:');

  const files = fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png'));
  files.forEach((file, index) => {
    console.log(`  ${index + 1}. ${file}`);
  });

  console.log(`\nTotal: ${files.length} screenshots\n`);
});
