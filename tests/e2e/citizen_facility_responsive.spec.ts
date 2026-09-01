import { test, expect } from '@playwright/test';

const VIEWPORT_SIZES = [
  { name: 'Mobile (390px)', width: 390, height: 844 },
  { name: 'Tablet (768px)', width: 768, height: 1024 },
  { name: 'Desktop (1440px)', width: 1440, height: 900 },
];

for (const vp of VIEWPORT_SIZES) {
  test.describe(`Citizen App - Responsive Facility Search [${vp.name}]`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test.beforeEach(async ({ page, context }) => {
      await context.grantPermissions(['geolocation']);
      await context.setGeolocation({ latitude: 18.5204, longitude: 73.8567 });

      await context.addInitScript(() => {
        localStorage.setItem('aarogya_locale', 'en-IN');
        localStorage.setItem('aarogya_user_language', 'en-IN');
        localStorage.setItem('aarogya_lang_confirmed', 'true');
        localStorage.setItem('aarogya_guest_session', JSON.stringify({
          session_id: 'guest-session-responsive-e2e',
          created_at: new Date().toISOString()
        }));
      });

      await page.goto('http://localhost:5173/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(400);
    });

    test(`Find health centre and view cards renders properly at ${vp.width}px`, async ({ page }) => {
      const homeFindHealthCentreBtn = page.locator('button:has-text("Find Health Centre")').first();
      await expect(homeFindHealthCentreBtn).toBeVisible({ timeout: 10000 });
      await homeFindHealthCentreBtn.click();

      // Verify category selection and search button
      const generalDoctorBtn = page.locator('button:has-text("General Doctor"), button:has-text("डॉक्टर / प्राथमिक आरोग्य केंद्र")').first();
      await expect(generalDoctorBtn).toBeVisible({ timeout: 10000 });
      await generalDoctorBtn.click();

      const findBtn = page.locator('#btn-find-suitable-facilities').first();
      await expect(findBtn).toBeVisible();
      await findBtn.click();

      // Verify facility cards are returned
      const firstCard = page.locator('[id^="btn-directions-"]').first();
      await expect(firstCard).toBeVisible({ timeout: 15000 });

      // Verify schedule OPD button is visible
      const opdBtn = page.locator('[id^="btn-schedule-opd-"]').first();
      await expect(opdBtn).toBeVisible();
    });
  });
}
