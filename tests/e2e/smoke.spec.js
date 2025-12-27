/**
 * Smoke Test - Basic Playwright Setup Verification
 * Ensures Playwright can navigate and interact with the Oxide dashboard
 */
import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should load the dashboard homepage', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');

    // Wait for any content to load (very basic check)
    await page.waitForLoadState('networkidle');

    // Verify page loaded
    expect(page.url()).toContain('localhost:3000');
  });

  test('should have basic page structure', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Check for any heading
    const headings = page.locator('h1, h2, h3');
    await expect(headings.first()).toBeVisible({ timeout: 10000 });
  });
});
