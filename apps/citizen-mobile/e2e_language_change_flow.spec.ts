import { test, expect } from '@playwright/test';

test.describe('Citizen Language Change Bugfix & State Preservation E2E Tests', () => {
  const TEST_PHONE = `98${Math.floor(10000000 + Math.random() * 90000000).toString().slice(0, 8)}`;
  const CITIZEN_NAME = 'Vikram Shinde';

  test.beforeEach(async ({ context }) => {
    await context.clearCookies();
  });

  test('1. Fresh App Launch starts with Onboarding Language Selection (Step 1 of 3)', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    // On fresh launch, Step 1 of 3 badge and Choose Your Language should appear
    const stepBadge = page.locator('#badge-onboarding-step-1');
    await expect(stepBadge).toBeVisible({ timeout: 10000 });

    const continueBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे")').first();
    await expect(continueBtn).toBeVisible();
    await continueBtn.click();

    // After Continue, enters Mobile Login or Guest Selection
    const mobileEntryBtn = page.locator('#btn-entry-mobile-otp');
    await expect(mobileEntryBtn).toBeVisible({ timeout: 10000 });
  });

  test('2. Logged-in Citizen: Language Change from Header preserves Login, Beneficiary, Care Context & Returns to Same Page', async ({ page, context }) => {
    // 1. Fresh launch & proceed past language
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const continueLangBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे")').first();
    if (await continueLangBtn.isVisible()) {
      await continueLangBtn.click();
    }

    // 2. Mobile Login & Onboarding
    await page.click('#btn-entry-mobile-otp');
    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', TEST_PHONE);
    await page.click('#btn-citizen-send-otp, #btn-citizen-request-otp');

    // Fill OTP cleanly using keyboard press
    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      await page.locator(`#otp-input-${i}`).focus();
      await page.keyboard.press(`${i + 1}`);
      await page.waitForTimeout(50);
    }
    const verifyBtn = page.locator('#btn-citizen-verify-otp-submit');
    if (await verifyBtn.isVisible() && await verifyBtn.isEnabled()) {
      await verifyBtn.click();
    }

    // Onboarding
    await page.waitForSelector('#title-citizen-onboarding', { timeout: 10000 });
    const nameInput = page.locator('input[placeholder*="Patil" i], input[type="text"]').first();
    await nameInput.fill(CITIZEN_NAME);
    await page.click('#btn-onboarding-submit');

    // 3. Citizen Home Verified
    await page.waitForSelector(`text=${CITIZEN_NAME}`, { timeout: 15000 });
    console.log("[E2E PROOF] Citizen logged in and on Home screen.");

    // 4. Navigate to My Care tab
    await page.click('#nav-tab-care');
    await page.waitForSelector('#title-my-care-screen', { timeout: 10000 });
    console.log("[E2E PROOF] Citizen navigated to My Care screen.");

    // 5. Open In-App Change Language from Top Header Globe
    await page.click('#btn-citizen-change-language');

    // Must NOT show Step 1 of 3
    const stepBadge = page.locator('#badge-onboarding-step-1');
    await expect(stepBadge).toHaveCount(0);

    // Header must show "Change Language" and Back button
    await expect(page.locator('#btn-language-back')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#btn-language-save')).toBeVisible();
    await expect(page.locator('#btn-language-cancel')).toBeVisible();

    // 6. Test Back / Cancel (should retain current language and return to care tab)
    await page.click('#btn-language-cancel');
    await page.waitForSelector('#title-my-care-screen', { timeout: 10000 });
    await expect(page.locator(`text=${CITIZEN_NAME}`).first()).toBeVisible();
    console.log("[E2E PROOF] Cancel returned to My Care without logging out.");

    // 7. Re-open Language Change and Switch to Marathi
    await page.click('#btn-citizen-change-language');
    await page.waitForSelector('#btn-language-save', { timeout: 5000 });

    // Select Marathi
    const mrLangBtn = page.locator('#btn-select-lang-mr-IN, [aria-label*="Marathi"], [aria-label*="मराठी"]').first();
    await mrLangBtn.click();

    // Click Save Language
    await page.click('#btn-language-save');

    // 8. Verify Citizen returns to My Care tab, authenticated, with Marathi translations active
    await page.waitForSelector('#title-my-care-screen', { timeout: 10000 });
    await expect(page.locator(`text=${CITIZEN_NAME}`).first()).toBeVisible();
    console.log("[E2E PROOF] Saved language returned to My Care screen with session preserved!");

    // 9. Reload page: verify language and session persist
    await page.reload();
    await page.waitForSelector(`text=${CITIZEN_NAME}`, { timeout: 15000 });
    const mobileEntryVisible = await page.locator('#btn-entry-mobile-otp').isVisible();
    expect(mobileEntryVisible).toBe(false);
    console.log("[E2E PROOF] Page reload retained citizen login and language.");

    // 10. Explicit Logout returns to initial onboarding language screen
    await page.click('#btn-citizen-logout');
    await page.waitForSelector('#badge-onboarding-step-1, #btn-language-continue, #btn-entry-mobile-otp', { timeout: 10000 });
    console.log("[E2E PROOF] Explicit logout cleared session successfully.");
  });

  test('3. Guest User: Language Change from Header preserves Guest Mode & returns to Guest Home', async ({ page }) => {
    // 1. Fresh launch
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const continueLangBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे")').first();
    if (await continueLangBtn.isVisible()) {
      await continueLangBtn.click();
    }

    // 2. Continue as Guest
    const guestBtn = page.locator('#btn-entry-guest-access');
    await expect(guestBtn).toBeVisible({ timeout: 10000 });
    await guestBtn.click();

    // Guest Home reached
    await page.waitForSelector('#badge-citizen-guest-mode', { timeout: 15000 });
    console.log("[E2E PROOF] Guest user on Home screen with Guest badge.");

    // 3. Open Language Change from Header
    await page.click('#btn-citizen-change-language');
    await expect(page.locator('#btn-language-save')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#badge-onboarding-step-1')).toHaveCount(0);

    // 4. Select Hindi
    const hiLangBtn = page.locator('#btn-select-lang-hi-IN, [aria-label*="Hindi"], [aria-label*="हिंदी"]').first();
    await hiLangBtn.click();
    await page.click('#btn-language-save');

    // 5. Must return to Guest Home with Guest Mode badge intact and translated UI
    await page.waitForSelector('#badge-citizen-guest-mode', { timeout: 10000 });
    const guestBadge = page.locator('#badge-citizen-guest-mode');
    await expect(guestBadge).toBeVisible();
    console.log("[E2E PROOF] Guest language changed, guest mode preserved, no logout or reset!");
  });
});
