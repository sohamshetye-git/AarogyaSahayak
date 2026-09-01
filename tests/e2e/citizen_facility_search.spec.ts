import { test, expect } from '@playwright/test';

test.describe('Citizen App - Find Health Centre Flow', () => {
  test.beforeEach(async ({ page, context }) => {
    // Grant geolocation permissions and mock coordinates
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 18.5204, longitude: 73.8567 });

    // Pre-seed localStorage to land directly on authenticated/guest home
    await context.addInitScript(() => {
      localStorage.setItem('aarogya_locale', 'en-IN');
      localStorage.setItem('aarogya_user_language', 'en-IN');
      localStorage.setItem('aarogya_lang_confirmed', 'true');
      localStorage.setItem('aarogya_guest_session', JSON.stringify({
        session_id: 'guest-session-e2e-1',
        created_at: new Date().toISOString()
      }));
    });

    // Navigate to citizen mobile app
    await page.goto('http://localhost:5173/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500);
  });

  test('Find Suitable Health Centres workflow end-to-end with real facilities', async ({ page }) => {
    // Navigate via Home Screen Find Health Centre action card
    const homeFindHealthCentreBtn = page.locator('button:has-text("Find Health Centre")').first();
    await expect(homeFindHealthCentreBtn).toBeVisible({ timeout: 10000 });
    await homeFindHealthCentreBtn.click();

    // Check that categories are rendered
    const generalDoctorBtn = page.locator('button:has-text("General Doctor"), button:has-text("डॉक्टर / प्राथमिक आरोग्य केंद्र")').first();
    await expect(generalDoctorBtn).toBeVisible({ timeout: 10000 });
    await generalDoctorBtn.click();

    // Click "Find Suitable Health Centres"
    const findBtn = page.locator('#btn-find-suitable-facilities, button:has-text("Find Suitable Health Centres"), button:has-text("योग्य आरोग्य केंद्रे शोधा")').first();
    await expect(findBtn).toBeVisible({ timeout: 10000 });
    await expect(findBtn).toBeEnabled();
    await findBtn.click();

    // Verify search results are displayed and not generic error
    await expect(page.locator('text=Health-centre search is temporarily unavailable')).not.toBeVisible();
    
    // Facility results list check
    const facilityCards = page.locator('[id^="btn-directions-"], [id^="btn-schedule-opd-"]');
    await expect(facilityCards.first()).toBeVisible({ timeout: 15000 });
  });

  test('Emergency care workflow provides 108 confirmation modal', async ({ page }) => {
    // Navigate via Home Screen Find Health Centre action card
    const homeFindHealthCentreBtn = page.locator('button:has-text("Find Health Centre")').first();
    await expect(homeFindHealthCentreBtn).toBeVisible({ timeout: 10000 });
    await homeFindHealthCentreBtn.click();

    const emergencyBtn = page.locator('button:has-text("Emergency Care"), button:has-text("आपत्कालीन व अपघात")').first();
    await expect(emergencyBtn).toBeVisible({ timeout: 10000 });
    await emergencyBtn.click();

    const emergency108 = page.locator('#btn-emergency-108-banner, #btn-emergency-108-header').first();
    await expect(emergency108).toBeVisible({ timeout: 5000 });
    await emergency108.click();

    // Confirmation modal should appear
    await expect(page.locator('text=Call 108 Emergency Ambulance?')).toBeVisible();
    const cancelBtn = page.locator('#btn-cancel-emergency-call');
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();
    await expect(page.locator('text=Call 108 Emergency Ambulance?')).not.toBeVisible();
  });
});
