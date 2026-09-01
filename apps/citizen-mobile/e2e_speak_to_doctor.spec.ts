import { test, expect } from '@playwright/test';

test.describe('Citizen Speak to Doctor E2E Workflow', () => {
  test('Complete flow: Patient selection -> Doctor request -> Direct requests visibility', async ({ page }) => {
    // 1. Open Citizen Mobile
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    // If language selection is shown, pick Marathi or English
    const continueBtn = page.locator('button:has-text("Continue"), button:has-text("पुढे जा")').first();
    if (await continueBtn.isVisible()) {
      await continueBtn.click();
    }

    // Authenticate with Mobile Number for Doctor Consultation flow
    const mobileEntryBtn = page.locator('#btn-entry-mobile-otp, button:has-text("Continue with Mobile Number")').first();
    await expect(mobileEntryBtn).toBeVisible({ timeout: 10000 });
    await mobileEntryBtn.click();

    await page.waitForSelector('#input-citizen-phone', { timeout: 10000 });
    await page.fill('#input-citizen-phone', '9820005544');
    await page.click('#btn-citizen-request-otp, #btn-citizen-send-otp');

    await page.waitForSelector('#otp-input-0', { timeout: 10000 });
    for (let i = 0; i < 6; i++) {
      await page.fill(`#otp-input-${i}`, `${i + 1}`);
    }
    const verifyBtn = page.locator('#btn-citizen-verify-otp-submit');
    if (await verifyBtn.isVisible() && await verifyBtn.isEnabled()) {
      await verifyBtn.click();
    }

    // If onboarding shown, complete registration
    const onboardingTitle = page.locator('#title-citizen-onboarding');
    if (await onboardingTitle.isVisible({ timeout: 4000 }).catch(() => false)) {
      const nameInput = page.locator('#input-onboarding-fullname, input[placeholder*="Patil" i], input[type="text"]').first();
      await nameInput.fill('Sunita Devi');
      const submitBtn = page.locator('#btn-onboarding-submit, button:has-text("Complete Registration")').first();
      await expect(submitBtn).toBeEnabled({ timeout: 5000 });
      await submitBtn.click();
    }

    // 2. Wait for Home screen and click "Speak to Doctor"
    await page.waitForSelector('text=Sunita Devi, #btn-home-speak-to-doctor', { timeout: 15000 });
    await page.waitForSelector('#btn-home-speak-to-doctor', { timeout: 15000 });
    await page.click('#btn-home-speak-to-doctor');

    // 3. Step 1: Beneficiary Selection - Verify Sunita Devi is loaded and selectable
    await page.waitForSelector('text=Sunita Devi', { timeout: 10000 });
    const sunitaCard = page.locator('text=Sunita Devi').first();
    await expect(sunitaCard).toBeVisible();
    await sunitaCard.click();

    // Click "Continue with Sunita" (Ensuring no Cannot read properties of undefined error!)
    const step1ContinueBtn = page.locator('button:has-text("Continue with Sunita"), button:has-text("Continue")').first();
    await expect(step1ContinueBtn).toBeEnabled();
    await step1ContinueBtn.click();

    // 4. Step 2: Health Concern Intake
    await page.waitForSelector('text=Describe Health Concern, text=समस्या सांगा, text=स्वास्थ्य समस्या बताएं', { timeout: 10000 });
    
    // Switch to Type mode
    const typeBtn = page.locator('button:has-text("Type"), button:has-text("लिहा")').first();
    await typeBtn.click();

    const textarea = page.locator('textarea');
    await textarea.fill('Severe persistent headache and mild dizziness for 2 days.');

    const step2ContinueBtn = page.locator('button:has-text("Continue to Channel Selection")');
    await step2ContinueBtn.click();

    // 5. Step 3: Channel Selection
    await page.waitForSelector('text=Select Consultation Channel, text=सल्लामसलत माध्यम निवडा', { timeout: 10000 });
    const step3ContinueBtn = page.locator('button:has-text("Confirm Channel & Proceed")');
    await step3ContinueBtn.click();

    // 6. Step 4: Location Confirmation
    await page.waitForSelector('text=Confirm Care Location, text=स्थानाची पुष्टी करा', { timeout: 10000 });
    const step4ContinueBtn = page.locator('button:has-text("Continue to Sharing Scope")');
    await step4ContinueBtn.click();

    // 7. Step 5: Sharing Scope
    await page.waitForSelector('text=Consented Sharing Scope, text=माहिती सामायिकरण व्याप्ती', { timeout: 10000 });
    const step5ContinueBtn = page.locator('button:has-text("Review & Give Explicit Consent")');
    await step5ContinueBtn.click();

    // 8. Step 6: Explicit Consent & Submission
    await page.waitForSelector('text=Explicit Consent & Submit, text=संमती व सबमिट करा', { timeout: 10000 });
    
    // Checkbox is unchecked by default -> Verify Submit is disabled
    const submitBtn = page.locator('button:has-text("Submit Request")');
    await expect(submitBtn).toBeDisabled();

    // Check explicit consent
    const consentCheckbox = page.locator('input[type="checkbox"]').first();
    await consentCheckbox.check();
    await expect(submitBtn).toBeEnabled();

    // Submit request
    await submitBtn.click();

    // 9. Verifies redirection to Doctor Waiting Room / Confirmation
    await page.waitForSelector('text=Doctor Consultation, text=Doctor Waiting Room, text=Waiting for Doctor, text=परामर्श', { timeout: 15000 });
  });
});
