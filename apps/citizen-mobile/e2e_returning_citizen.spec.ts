import { test, expect } from '@playwright/test';

test.describe('Returning Citizen Production-Grade Login Journey', () => {
  const TEST_PHONE = "9821998877";

  test('Full Journey: First Login -> Onboarding -> Create Care Request -> Logout -> Return Login -> Restore Account & Records -> Session Refresh', async ({ page, request }) => {
    // Step 1: Open Citizen Mobile App
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Language selection if present
    const continueBtn = page.locator('button:has-text("Continue"), button:has-text("पुढे जा")').first();
    if (await continueBtn.isVisible()) {
      await continueBtn.click();
    }

    // Step 2: Choose "Continue with Mobile Number"
    const mobileEntryBtn = page.locator('#btn-entry-mobile-otp, button:has-text("Continue with Mobile Number"), button:has-text("मोबाईल")').first();
    await expect(mobileEntryBtn).toBeVisible({ timeout: 10000 });
    await mobileEntryBtn.click();

    // Step 3: Enter Phone Number
    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', TEST_PHONE);

    const getOtpBtn = page.locator('#btn-citizen-request-otp, button:has-text("Get Verification Code"), button:has-text("ओटीपी")').first();
    await getOtpBtn.click();

    // Step 4: Enter OTP
    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      await page.fill(`#otp-input-${i}`, `${i + 1}`);
    }

    const verifyBtn = page.locator('#btn-citizen-verify-otp-submit');
    await expect(verifyBtn).toBeEnabled();
    await verifyBtn.click();

    // Step 5: For genuinely new number, Onboarding Screen must open
    await page.waitForSelector('text=Complete Registration, text=नोंदणी पूर्ण करा, text=पंजीकरण पूर्ण करें', { timeout: 10000 });

    // Fill minimal onboarding details
    const nameInput = page.locator('input[placeholder*="Patil" i], input[type="text"]').first();
    await nameInput.fill('Ananya Deshmukh');

    const finishOnboardingBtn = page.locator('button:has-text("Complete Registration"), button:has-text("नोंदणी पूर्ण करा")').first();
    await finishOnboardingBtn.click();

    // Step 6: Authenticated Home Screen is reached
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 15000 });
    console.log("[E2E PROOF] Step 1-6 Complete: First login + onboarding established canonical identity.");

    // Step 7: Create a Care Request (Speak to Doctor)
    const speakToDoctorBtn = page.locator('text=Speak to Doctor, text=डॉक्टरांशी बोला, text=डॉक्टर से बात करें').first();
    await expect(speakToDoctorBtn).toBeVisible({ timeout: 10000 });
    await speakToDoctorBtn.click();

    // Select Beneficiary
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 10000 });
    const selfCard = page.locator('text=Ananya Deshmukh').first();
    await selfCard.click();

    const step1ContinueBtn = page.locator('button:has-text("Continue")').first();
    await step1ContinueBtn.click();

    // Fill Health Concern
    await page.waitForSelector('text=Describe Health Concern, text=समस्या सांगा', { timeout: 10000 });
    const typeBtn = page.locator('button:has-text("Type"), button:has-text("लिहा")').first();
    if (await typeBtn.isVisible()) await typeBtn.click();
    await page.locator('textarea').fill('Routine antenatal blood pressure checkup and nutrition guidance.');

    await page.locator('button:has-text("Continue to Channel Selection")').click();
    await page.waitForSelector('text=Select Consultation Channel', { timeout: 10000 });
    await page.locator('button:has-text("Confirm Channel & Proceed")').click();

    await page.waitForSelector('text=Confirm Care Location', { timeout: 10000 });
    await page.locator('button:has-text("Continue to Sharing Scope")').click();

    await page.waitForSelector('text=Consented Sharing Scope', { timeout: 10000 });
    await page.locator('button:has-text("Review & Give Explicit Consent")').click();

    await page.waitForSelector('text=Explicit Consent & Submit', { timeout: 10000 });
    const consentCheckbox = page.locator('input[type="checkbox"]').first();
    await consentCheckbox.check();

    const submitCareBtn = page.locator('button:has-text("Submit Request")');
    await expect(submitCareBtn).toBeEnabled();
    await submitCareBtn.click();

    await page.waitForSelector('text=Doctor Consultation, text=Doctor Waiting Room, text=Waiting for Doctor', { timeout: 15000 });
    console.log("[E2E PROOF] Step 7 Complete: Care request created for citizen.");

    // Step 8: Return to Home & Perform Explicit Logout
    await page.goto('http://localhost:5173');
    await page.waitForSelector('#btn-citizen-logout', { timeout: 10000 });
    await page.click('#btn-citizen-logout');

    // Verify session revoked and returned to Entry Selection
    await page.waitForSelector('#btn-entry-mobile-otp', { timeout: 10000 });
    console.log("[E2E PROOF] Step 8 Complete: Explicit logout revoked session cleanly.");

    // Step 9: Login later with the SAME number and a new OTP
    await page.click('#btn-entry-mobile-otp');
    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', TEST_PHONE);
    await page.click('#btn-citizen-request-otp');

    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      await page.fill(`#otp-input-${i}`, `${i + 1}`);
    }
    await page.click('#btn-citizen-verify-otp-submit');

    // Step 10: Onboarding MUST be skipped, directly restoring citizen home & identity
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 15000 });
    const onboardingVisible = await page.locator('text=Complete Registration, text=नोंदणी पूर्ण करा').isVisible();
    expect(onboardingVisible).toBe(false);
    console.log("[E2E PROOF] Step 9-10 Complete: Onboarding was skipped and existing account restored.");

    // Step 11: Refresh page -> Session remains authenticated without requesting OTP
    await page.reload();
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 15000 });
    console.log("[E2E PROOF] Step 11 Complete: Browser refresh restored session without OTP.");
  });
});
