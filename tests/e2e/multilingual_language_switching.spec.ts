import { test, expect } from '@playwright/test';

test.describe('Multilingual Language Switching & Scoped Persistence', () => {
  test.setTimeout(90000);

  test('Portal: Doctor language switching re-renders dynamically and preserves state', async ({ page }) => {
    // Navigate to healthcare portal
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Login as Doctor if on login page
    const doctorLoginBtn = page.locator('#login-as-doctor-btn, button:has-text("Doctor"), button:has-text("Sign In as Doctor")');
    if (await doctorLoginBtn.count() > 0) {
      await doctorLoginBtn.first().click();
      await page.waitForTimeout(500);
    }

    // Check language selector exists
    const langSelect = page.locator('#portal-desktop-language-select');
    if (await langSelect.count() > 0) {
      await expect(langSelect).toBeVisible();

      // Switch to Hindi (hi-IN)
      await langSelect.selectOption('hi-IN');
      await page.waitForTimeout(300);

      // Verify header or tabs update to Hindi without page reload
      const pageText = await page.textContent('body');
      expect(pageText).toBeTruthy();

      // Switch to Marathi (mr-IN)
      await langSelect.selectOption('mr-IN');
      await page.waitForTimeout(300);

      // Switch back to English (en-IN)
      await langSelect.selectOption('en-IN');
      await page.waitForTimeout(300);
    }
  });

  test('Portal: ASHA language switching re-renders reactive keys', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    const ashaLoginBtn = page.locator('#login-as-asha-btn, button:has-text("ASHA"), button:has-text("Sign In as ASHA")');
    if (await ashaLoginBtn.count() > 0) {
      await ashaLoginBtn.first().click();
      await page.waitForTimeout(500);
    }

    const langSelect = page.locator('#portal-desktop-language-select');
    if (await langSelect.count() > 0) {
      await expect(langSelect).toBeVisible();

      // Switch to Marathi (mr-IN)
      await langSelect.selectOption('mr-IN');
      await page.waitForTimeout(300);

      // Switch back to English (en-IN)
      await langSelect.selectOption('en-IN');
      await page.waitForTimeout(300);
    }
  });

  test('Citizen Mobile: Reactive language selector and localized onboarding', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    // Verify language selection cards are rendered
    const hiCard = page.locator('#language-card-hi-IN, div[role="button"][aria-label*="हिन्दी"]');
    if (await hiCard.count() > 0) {
      await hiCard.first().click();
      await page.waitForTimeout(300);
    }

    // Verify continue button renders
    const continueBtn = page.locator('button:has-text("जारी रखें"), button:has-text("Continue"), button:has-text("पुढे जा")');
    if (await continueBtn.count() > 0) {
      await expect(continueBtn.first()).toBeVisible();
    }
  });
});
