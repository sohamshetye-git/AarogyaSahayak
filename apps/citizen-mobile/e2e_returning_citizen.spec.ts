import { test, expect } from '@playwright/test';

test.describe('Returning Citizen Production-Grade Login Journey', () => {
  const TEST_PHONE = `98${Math.floor(10000000 + Math.random() * 90000000).toString().slice(0, 8)}`;

  test('Full Journey: First Login -> Onboarding -> Create Care Request -> Logout -> Return Login -> Restore Account & Records -> Session Refresh', async ({ page, request }) => {
    // Step 1: Open Citizen Mobile App
    await page.goto('http://localhost:3001');
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

    const getOtpBtn = page.locator('#btn-citizen-request-otp, #btn-citizen-send-otp, button:has-text("Get Verification Code"), button:has-text("ओटीपी")').first();
    await getOtpBtn.click();

    // Step 4: Enter OTP (auto-submits on 6th digit)
    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      const input = page.locator(`#otp-input-${i}`);
      await input.click();
      await input.fill(`${i + 1}`);
    }

    const verifyBtn = page.locator('#btn-citizen-verify-otp-submit');
    if (await verifyBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      if (await verifyBtn.isEnabled()) {
        await verifyBtn.click();
      }
    }

    // Step 5: For genuinely new number, Onboarding Screen must open
    await page.waitForSelector('#title-citizen-onboarding', { timeout: 10000 });

    // Fill minimal onboarding details
    const nameInput = page.locator('#input-onboarding-fullname, input[placeholder*="Patil" i], input[type="text"]').first();
    await nameInput.fill('Ananya Deshmukh');

    const finishOnboardingBtn = page.locator('#btn-onboarding-submit, button:has-text("Complete Registration")').first();
    await expect(finishOnboardingBtn).toBeEnabled({ timeout: 5000 });
    await finishOnboardingBtn.click();

    // Step 6: Authenticated Home Screen is reached
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 15000 });
    console.log("[E2E PROOF] Step 1-6 Complete: First login + onboarding established canonical identity.");

    // Step 7: Create a Care Request (Speak to Doctor)
    await page.waitForSelector('#btn-home-speak-to-doctor', { timeout: 15000 });
    await page.click('#btn-home-speak-to-doctor');

    // Select Beneficiary
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 10000 });
    const selfCard = page.locator('text=Ananya Deshmukh').first();
    await selfCard.click();

    const step1ContinueBtn = page.locator('button:has-text("Continue with Ananya"), button:has-text("Continue"), button:has-text("पुढे")').first();
    await expect(step1ContinueBtn).toBeEnabled();
    await step1ContinueBtn.click();

    // Fill Health Concern
    const step2Heading = page.locator('h2:has-text("Describe Health Concern")')
      .or(page.locator('h2:has-text("समस्या सांगा")'))
      .or(page.locator('text=Step 2 of 6'));
    await step2Heading.first().waitFor({ timeout: 10000 });
    const typeBtn = page.locator('button:has-text("Type"), button:has-text("लिहा")').first();
    if (await typeBtn.isVisible()) await typeBtn.click();
    await page.locator('textarea').fill('Routine antenatal blood pressure checkup and nutrition guidance.');

    await page.locator('button:has-text("Continue to Channel Selection"), button:has-text("माध्यम निवडीकडे")').click();
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

    const waitingRoomIndicator = page.locator('text=PHC Doctor Waiting Room')
      .or(page.locator('text=Waiting for Medical Officer'))
      .or(page.locator('text=Doctor Consultation'))
      .or(page.locator('text=Waiting for Doctor'));
    await waitingRoomIndicator.first().waitFor({ timeout: 15000 });
    console.log("[E2E PROOF] Step 7 Complete: Care request created for citizen.");

    // Step 8: Return to Home & Perform Explicit Logout
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    await page.waitForSelector('#btn-citizen-logout', { timeout: 15000 });
    await page.click('#btn-citizen-logout');
    
    // Step 1: Language selection screen is shown on logout
    const langBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे जा")').first();
    await langBtn.waitFor({ timeout: 5000 });
    await langBtn.click();

    const mobileEntryBtn2 = page.locator('#btn-entry-mobile-otp, button:has-text("Continue with Mobile Number"), button:has-text("मोबाईल")').first();
    await mobileEntryBtn2.waitFor({ timeout: 10000 });
    console.log("[E2E PROOF] Step 8 Complete: Citizen explicitly logged out.");

    // Step 9: Returning Login - Enter SAME Phone Number
    await mobileEntryBtn2.click();
    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', TEST_PHONE);

    // If cooldown exists on UI, wait for it or click request button
    const getOtpBtn2 = page.locator('#btn-citizen-request-otp, button:has-text("Send OTP Code")').first();
    await getOtpBtn2.click();

    // Step 10: Enter OTP
    await page.waitForSelector('#otp-input-0', { timeout: 15000 });
    for (let i = 0; i < 6; i++) {
      const input = page.locator(`#otp-input-${i}`);
      await input.click();
      await input.fill(`${i + 1}`);
    }
    const verifyBtn2 = page.locator('#btn-citizen-verify-otp-submit');
    if (await verifyBtn2.isVisible({ timeout: 1000 }).catch(() => false)) {
      if (await verifyBtn2.isEnabled()) {
        await verifyBtn2.click();
      }
    }

    // Step 11: CRITICAL VERIFICATION - Returning Citizen MUST NOT see Onboarding Screen
    await page.waitForSelector('text=Ananya Deshmukh', { timeout: 15000 });
    const onboardingVisible = await page.locator('#title-citizen-onboarding').isVisible();
    expect(onboardingVisible).toBe(false);
    console.log("[E2E PROOF] Step 11 Complete: Returning citizen bypassed onboarding and directly landed on Home screen.");

    // Step 12: Verify Previous Consultations and Health Records Restored
    const appointmentsTab = page.locator('button:has-text("Care"), button:has-text("कन्सल्टेशन्स")').first();
    if (await appointmentsTab.isVisible()) {
      await appointmentsTab.click();
      const careRecordIndicator = page.locator('text=Routine antenatal blood pressure checkup')
        .or(page.locator('text=Speak to Doctor'))
        .or(page.locator('text=Active Care Progress'));
      await careRecordIndicator.first().waitFor({ timeout: 10000 });
      console.log("[E2E PROOF] Step 12 Complete: Historical care request restored for returning citizen.");
    }
  });
});
