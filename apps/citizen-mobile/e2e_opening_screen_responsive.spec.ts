import { test, expect } from '@playwright/test';

test.describe('Citizen Mobile Opening Screen Responsive & Flow Tests', () => {
  const VIEWPORTS = [
    { name: '320x568 (iPhone SE / Smallest)', width: 320, height: 568 },
    { name: '360x800 (Galaxy S20)', width: 360, height: 800 },
    { name: '390x844 (iPhone 12/13/14)', width: 390, height: 844 },
    { name: '412x915 (Pixel 7)', width: 412, height: 915 },
    { name: '430x932 (iPhone 14 Pro Max)', width: 430, height: 932 },
    { name: '768x1024 (Tablet Preview)', width: 768, height: 1024 },
    { name: '1440x900 (Desktop Centered Preview)', width: 1440, height: 900 }
  ];

  for (const vp of VIEWPORTS) {
    test(`Viewport ${vp.name}: No horizontal overflow, all controls visible and properly sized`, async ({ page, context }) => {
      await context.clearCookies();
      await page.setViewportSize({ width: vp.width, height: vp.height });

      await page.goto('http://localhost:3001');
      await page.waitForLoadState('networkidle');

      // If language screen shows on first launch, click Continue
      const langContinueBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे जा")').first();
      if (await langContinueBtn.isVisible({ timeout: 2000 })) {
        await langContinueBtn.click();
      }

      // Verify Citizen Entry Screen Header & Actions
      const mobileBtn = page.locator('#btn-entry-mobile-otp');
      const guestBtn = page.locator('#btn-entry-guest-access');
      const emergencyBtn = page.locator('#btn-emergency-108-entry');
      const langSelector = page.locator('#btn-entry-language-selector');
      const speakBtn = page.locator('#btn-entry-speak-selection');
      const hearBtn = page.locator('#btn-entry-hear-options');

      await expect(mobileBtn).toBeVisible({ timeout: 10000 });
      await expect(guestBtn).toBeVisible();
      await expect(emergencyBtn).toBeVisible();
      await expect(langSelector).toBeVisible();
      await expect(speakBtn).toBeVisible();
      await expect(hearBtn).toBeVisible();

      // Check horizontal overflow: scrollWidth must equal clientWidth
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      expect(hasHorizontalScroll).toBe(false);

      // Check touch target height minimums (>= 44px / 48px)
      const mobileBox = await mobileBtn.boundingBox();
      const guestBox = await guestBtn.boundingBox();
      const emergencyBox = await emergencyBtn.boundingBox();
      const speakBox = await speakBtn.boundingBox();
      const hearBox = await hearBtn.boundingBox();

      expect(mobileBox?.height).toBeGreaterThanOrEqual(48);
      expect(guestBox?.height).toBeGreaterThanOrEqual(48);
      expect(emergencyBox?.height).toBeGreaterThanOrEqual(44);
      expect(speakBox?.height).toBeGreaterThanOrEqual(44);
      expect(hearBox?.height).toBeGreaterThanOrEqual(44);

      // On mobile <= 480px, the entry card should occupy 100% width (or close to container)
      if (vp.width <= 480) {
        const containerBox = await page.locator('main').boundingBox();
        expect(containerBox?.width).toBeGreaterThanOrEqual(vp.width - 2);
      }
    });
  }

  test('Multi-language switching: Hindi, Marathi, Tamil, Bengali update text dynamically', async ({ page, context }) => {
    await context.clearCookies();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const langContinueBtn = page.locator('#btn-language-continue').first();
    if (await langContinueBtn.isVisible({ timeout: 2000 })) {
      await langContinueBtn.click();
    }

    const langSelector = page.locator('#btn-entry-language-selector');
    await expect(langSelector).toBeVisible({ timeout: 8000 });

    // Test Hindi
    await langSelector.click();
    const hiOption = page.locator('role=option >> text=हिंदी').first();
    await hiOption.click();
    await expect(page.locator('#btn-entry-mobile-otp')).toContainText('मोबाइल नंबर से आगे बढ़ें');

    // Test Tamil
    await langSelector.click();
    const taOption = page.locator('role=option >> text=தமிழ்').first();
    await taOption.click();
    await expect(page.locator('#btn-entry-mobile-otp')).toContainText('மொபைல் எண்ணுடன் தொடரவும்');

    // Test Bengali
    await langSelector.click();
    const bnOption = page.locator('role=option >> text=বাংলা').first();
    await bnOption.click();
    await expect(page.locator('#btn-entry-mobile-otp')).toContainText('মোবাইল নম্বর দিয়ে চালিয়ে যান');

    // Test Marathi
    await langSelector.click();
    const mrOption = page.locator('role=option >> text=मराठी').first();
    await mrOption.click();
    await expect(page.locator('#btn-entry-mobile-otp')).toContainText('मोबाईल नंबरने सुरू ठेवा');
  });

  test('Emergency 108 action opens safety confirmation sheet and does not call prematurely', async ({ page, context }) => {
    await context.clearCookies();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const langContinueBtn = page.locator('#btn-language-continue').first();
    if (await langContinueBtn.isVisible({ timeout: 2000 })) {
      await langContinueBtn.click();
    }

    const emergencyBtn = page.locator('#btn-emergency-108-entry');
    await expect(emergencyBtn).toBeVisible({ timeout: 8000 });
    await emergencyBtn.click();

    // Verification modal dialog
    const modalTitle = page.locator('#emergency-dialog-title');
    await expect(modalTitle).toBeVisible();

    const confirmDialBtn = page.locator('#btn-confirm-dial-108');
    await expect(confirmDialBtn).toBeVisible();
    expect(await confirmDialBtn.getAttribute('href')).toBe('tel:108');

    // Cancel modal
    const cancelBtn = page.locator('#btn-cancel-emergency-dialog');
    await cancelBtn.click();
    await expect(modalTitle).not.toBeVisible();
  });

  test('Primary action: Mobile login routes to Phone/OTP verification flow', async ({ page, context }) => {
    await context.clearCookies();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const langContinueBtn = page.locator('#btn-language-continue').first();
    if (await langContinueBtn.isVisible({ timeout: 2000 })) {
      await langContinueBtn.click();
    }

    const mobileBtn = page.locator('#btn-entry-mobile-otp');
    await expect(mobileBtn).toBeVisible({ timeout: 8000 });
    await mobileBtn.click();

    // Verify phone entry input is loaded
    await expect(page.locator('#input-citizen-phone')).toBeVisible({ timeout: 8000 });
  });

  test('Secondary action: Continue as Guest enters guest session and maintains guest workspace', async ({ page, context }) => {
    await context.clearCookies();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    const langContinueBtn = page.locator('#btn-language-continue').first();
    if (await langContinueBtn.isVisible({ timeout: 2000 })) {
      await langContinueBtn.click();
    }

    const guestBtn = page.locator('#btn-entry-guest-access');
    await expect(guestBtn).toBeVisible({ timeout: 8000 });
    await guestBtn.click();

    // Guest enters Home Screen workspace with Guest badge
    await expect(page.locator('#badge-citizen-guest-mode')).toBeVisible({ timeout: 10000 });
  });
});
