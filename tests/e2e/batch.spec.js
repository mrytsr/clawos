
const { test, expect } = require('@playwright/test');

test.describe('Batch Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Setup: Create some test files if needed, or assume files exist
    // For this test, we assume there are files in the file list
  });

  test('Multi-select triggers batch drawer with correct count', async ({ page }) => {
    // Select first file
    await page.locator('.file-checkbox').nth(0).check();
    
    // Verify drawer opens
    const drawer = page.locator('#batchDrawer');
    await expect(drawer).toHaveClass(/open/);
    await expect(page.locator('#batchCount')).toHaveText('已选 1 项');

    // Select second file
    await page.locator('.file-checkbox').nth(1).check();
    await expect(page.locator('#batchCount')).toHaveText('已选 2 项');
  });

  test('Batch Drawer does not have mask (allows interaction)', async ({ page }) => {
    // Select a file to open drawer
    await page.locator('.file-checkbox').nth(0).check();
    
    // Check that we can still click other elements (no backdrop blocking)
    // We verify this by checking if there is a backdrop with 'open' class
    // In our implementation, batchDrawer has no backdrop
    const backdrop = page.locator('.drawer-backdrop.open');
    await expect(backdrop).not.toBeVisible();
    
    // We can still check another box
    await page.locator('.file-checkbox').nth(1).check();
    await expect(page.locator('#batchCount')).toHaveText('已选 2 项');
  });

  test('Batch Copy flow', async ({ page }) => {
    // Select files
    await page.locator('.file-checkbox').nth(0).check();
    await page.locator('.file-checkbox').nth(1).check();
    
    // Click Batch Copy
    await page.click('#batchDrawer >> text=复制');
    
    // Verify clipboard bar shows up and drawer closes (selection cleared)
    await expect(page.locator('#clipboardBar')).toBeVisible();
    await expect(page.locator('#batchDrawer')).not.toHaveClass(/open/);
  });

  test('Batch Move flow', async ({ page }) => {
    // Select files
    await page.locator('.file-checkbox').nth(0).check();
    
    // Click Batch Move
    await page.click('#batchDrawer >> text=移动');
    
    // Verify clipboard bar shows up and drawer closes (selection cleared)
    await expect(page.locator('#clipboardBar')).toBeVisible();
    await expect(page.locator('#batchDrawer')).not.toHaveClass(/open/);
  });

  test('Clear Selection closes drawer', async ({ page }) => {
    await page.locator('.file-checkbox').nth(0).check();
    await expect(page.locator('#batchDrawer')).toHaveClass(/open/);
    
    await page.click('#batchDrawer .drawer-close-btn');
    
    await expect(page.locator('#batchDrawer')).not.toHaveClass(/open/);
    // Checkboxes should be unchecked
    expect(await page.locator('.file-checkbox').nth(0).isChecked()).toBeFalsy();
  });
});
