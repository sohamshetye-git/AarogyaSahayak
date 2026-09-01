import { test, expect } from '@playwright/test';

test.describe('Citizen Session Persistence & Lifecycle E2E Test', () => {
  const TEST_PHONE = `98${Math.floor(10000000 + Math.random() * 90000000).toString().slice(0, 8)}`;

  test('New Citizen: OTP -> Onboarding -> Home -> Reload -> Multi-Tab -> Logout', async ({ page, context, request }) => {
    // 1. Clear cookies & local storage
    await context.clearCookies();

    // 2. Open Citizen App
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    // Language selection on first launch
    const continueLangBtn = page.locator('button:has-text("Continue"), button:has-text("पुढे जा")').first();
    if (await continueLangBtn.isVisible()) {
      await continueLangBtn.click();
    }

    // 3. Mobile Number Entry
    const mobileEntryBtn = page.locator('#btn-entry-mobile-otp, button:has-text("Continue with Mobile Number"), button:has-text("मोबाईल")').first();
    await expect(mobileEntryBtn).toBeVisible({ timeout: 10000 });
    await mobileEntryBtn.click();

    // 4. Enter phone and request OTP
    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', TEST_PHONE);
    await page.click('#btn-citizen-send-otp, #btn-citizen-request-otp');

    // 5. Fill OTP 123456
    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      await page.fill(`#otp-input-${i}`, `${i + 1}`);
    }
    const verifyBtn = page.locator('#btn-citizen-verify-otp-submit');
    if (await verifyBtn.isVisible() && await verifyBtn.isEnabled()) {
      await verifyBtn.click();
    }

    // 6. Complete Onboarding
    await page.waitForSelector('#title-citizen-onboarding', { timeout: 10000 });
    const nameInput = page.locator('input[placeholder*="Patil" i], input[type="text"]').first();
    await nameInput.fill('Manav Raju Singh');

    await page.click('#btn-onboarding-submit');

    // 7. Authenticated Home Screen shows citizen name
    await page.waitForSelector('text=Manav Raju Singh', { timeout: 15000 });
    console.log("[E2E PROOF] Onboarding complete. Citizen Home displays 'Manav Raju Singh'.");

    // 8. Verify Cookie Set in Browser Context
    const cookiesAfterOnboarding = await context.cookies();
    const refreshCookie = cookiesAfterOnboarding.find(c => c.name === 'aarogya_citizen_refresh');
    expect(refreshCookie).toBeDefined();
    expect(refreshCookie?.httpOnly).toBe(true);
    expect(refreshCookie?.path).toBe('/');
    console.log("[E2E PROOF] 'aarogya_citizen_refresh' HttpOnly cookie confirmed:", refreshCookie?.name);

    // 9. RELOAD BROWSER (Session Restoration Check)
    console.log("[E2E PROOF] Reloading browser page...");
    await page.reload();

    // Verify "Restoring your account…" or immediate direct Home restoration
    await page.waitForSelector('text=Manav Raju Singh', { timeout: 15000 });
    
    // Welcome / Guest screen must NOT appear
    const mobileEntryVisible = await page.locator('#btn-entry-mobile-otp').isVisible();
    expect(mobileEntryVisible).toBe(false);
    console.log("[E2E PROOF] Reload restored session seamlessly. Mobile Entry Screen was NOT shown.");

    // 10. Open Second Tab in Same Browser Context
    console.log("[E2E PROOF] Opening second tab in same context...");
    const page2 = await context.newPage();
    await page2.goto('http://localhost:3001');
    await page2.waitForSelector('text=Manav Raju Singh', { timeout: 15000 });
    console.log("[E2E PROOF] Second tab immediately authenticated via HttpOnly cookie.");

    // 11. Explicit Logout
    await page.click('#btn-citizen-logout');
    await page.waitForSelector('#btn-language-continue, #btn-entry-mobile-otp', { timeout: 10000 });
    console.log("[E2E PROOF] Explicit logout completed.");

    // 12. Reload after Logout -> Must Require Onboarding / Login
    await page.reload();
    await page.waitForSelector('#btn-language-continue, #btn-entry-mobile-otp', { timeout: 10000 });
    console.log("[E2E PROOF] Reload after logout requires login as expected.");
    await page2.close();
  });
});
