import { test, expect } from '@playwright/test';

test.describe('Citizen Speak to Doctor E2E Workflow', () => {
  test('Complete flow: Patient selection -> Doctor request -> Direct requests visibility', async ({ page }) => {
    // 1. Open Citizen Mobile
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // If language selection is shown, pick Marathi or English
    const continueBtn = page.locator('button:has-text("Continue"), button:has-text("पुढे जा")');
    if (await continueBtn.isVisible()) {
      await continueBtn.click();
    }

    // 2. Click "Speak to Doctor" on Home screen
    const speakToDoctorBtn = page.locator('text=Speak to Doctor, text=डॉक्टरांशी बोला, text=डॉक्टर से बात करें').first();
    await expect(speakToDoctorBtn).toBeVisible({ timeout: 10000 });
    await speakToDoctorBtn.click();

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
