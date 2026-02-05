const { test, expect } = require('@playwright/test');

test('copy persists bar via localStorage and paste copies into folder', async ({ page }) => {
    await page.goto('/');

    const row = page.locator('.file-item', { hasText: 'abc.txt' });
    await expect(row).toBeVisible();
    await row.locator('.menu-btn').click();
    await page.locator('#menuModal .modal-item', { hasText: '复制' }).click();

    const bar = page.locator('#clipboardBar');
    await expect(bar).toBeVisible();
    await expect(page.locator('#clipboardLabel')).toHaveText(/在此粘贴 abc\.txt/);

    await page.reload();
    await expect(page.locator('#clipboardBar')).toBeVisible();

    const dstRow = page.locator('.file-item', { hasText: 'dst' });
    await expect(dstRow).toBeVisible();
    await dstRow.locator('a', { hasText: 'dst' }).click();

    await expect(page).toHaveURL(/\/browse/);
    await page.locator('#clipboardPasteBtn').click();

    await expect(page.locator('#clipboardBar')).toBeHidden();
    await expect(page.locator('.toast', { hasText: '粘贴成功' })).toBeVisible();
    await expect(page.locator('.file-item', { hasText: 'abc.txt' })).toBeVisible();
});

test('cut paste moves file and cancel clears state', async ({ page }) => {
    await page.goto('/');

    const row = page.locator('.file-item', { hasText: 'abc.txt' });
    await expect(row).toBeVisible();
    await row.locator('.menu-btn').click();
    await page.locator('#menuModal .modal-item', { hasText: '剪切' }).click();

    await expect(page.locator('#clipboardBar')).toBeVisible();
    await page.locator('#clipboardCancelBtn').click();
    await expect(page.locator('#clipboardBar')).toBeHidden();

    await page.reload();
    await expect(page.locator('#clipboardBar')).toBeHidden();
});

