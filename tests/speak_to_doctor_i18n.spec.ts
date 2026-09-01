import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

const SCREENSHOT_DIR = "C:/Users/lenovo/.gemini/antigravity-ide/brain/2403270a-13e3-4be2-84fd-c75287acffb2/screenshots";

test.beforeAll(() => {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
});

const languages = [
  { code: "hi-IN", name: "Hindi", prefix: "hi" },
  { code: "mr-IN", name: "Marathi", prefix: "mr" },
  { code: "gu-IN", name: "Gujarati", prefix: "gu" }
];

for (const lang of languages) {
  test(`Capture Speak to Doctor workflow in ${lang.name} (${lang.code})`, async ({ page }) => {
    test.setTimeout(90000);

    // 1. Visit Citizen App with local storage pre-configured
    await page.goto("http://localhost:3001");
    await page.evaluate(({ code }) => {
      localStorage.setItem("aarogya_locale", code);
      localStorage.setItem("aarogya_locale_confirmed", "true");
      // Set an authenticated citizen profile so they go straight to home
      localStorage.setItem("aarogya_citizen_user", JSON.stringify({
        id: "cit-test-user-01",
        name: "Sunita Devi",
        phone: "+919876543210",
        village: "Kalyanpur"
      }));
      localStorage.setItem("aarogya_citizen_session", JSON.stringify({
        token: "test-token-jwt",
        user_id: "cit-test-user-01"
      }));
    }, { code: lang.code });

    await page.reload();
    await page.waitForTimeout(2500);

    // 2. Open Speak to Doctor Wizard
    // Try to find the button
    const doctorBtn = page.locator("button:has-text('डॉक्टर'), button:has-text('Doctor'), button:has-text('ડોક્ટર')").first();
    if (await doctorBtn.isVisible()) {
      await doctorBtn.click();
    } else {
      // Direct click on first action card
      await page.locator("main button").first().click();
    }

    await page.waitForTimeout(1500);

    // STEP 1 -> Next to Step 2
    const contBtn = page.locator("button:has-text('पुढे'), button:has-text('आगे'), button:has-text('આગળ'), button:has-text('Continue')").first();
    if (await contBtn.isVisible()) {
      await contBtn.click();
    }
    await page.waitForTimeout(1000);

    // CAPTURE STEP 2 (Describe Health Concern)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${lang.prefix}_step2_health_concern.png`), fullPage: true });

    // Step 2 -> Step 3
    const contBtn2 = page.locator("button:has-text('पुढे'), button:has-text('आगे'), button:has-text('આગળ'), button:has-text('Continue')").first();
    await contBtn2.click();
    await page.waitForTimeout(1000);

    // Step 3 -> Step 4
    const contBtn3 = page.locator("button:has-text('पुढे'), button:has-text('आगे'), button:has-text('આગળ'), button:has-text('Continue')").first();
    await contBtn3.click();
    await page.waitForTimeout(1000);

    // Step 4 -> Step 5
    const contBtn4 = page.locator("button:has-text('पुढे'), button:has-text('आगे'), button:has-text('આગળ'), button:has-text('Continue')").first();
    await contBtn4.click();
    await page.waitForTimeout(1000);

    // CAPTURE STEP 5 (Sharing Scope)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${lang.prefix}_step5_sharing_scope.png`), fullPage: true });

    // Step 5 -> Step 6
    const contBtn5 = page.locator("button:has-text('पुढे'), button:has-text('आगे'), button:has-text('આગળ'), button:has-text('Continue')").first();
    await contBtn5.click();
    await page.waitForTimeout(1000);

    // CAPTURE STEP 6 (Explicit Consent and Submit)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${lang.prefix}_step6_consent_submit.png`), fullPage: true });

    // Check consent box
    const consentCheckbox = page.locator("input[type='checkbox']").last();
    await consentCheckbox.check({ force: true });
    await page.waitForTimeout(500);

    // Submit request
    const submitBtn = page.locator("button[type='submit'], button:has-text('सबमिट'), button:has-text('Submit'), button:has-text('દાખલ')").last();
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      await page.waitForTimeout(3000);

      // CAPTURE WAITING ROOM
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${lang.prefix}_waiting_room.png`), fullPage: true });
    }

    // Go to My Care Tab
    const myCareTab = page.locator("button:has-text('माझे उपचार'), button:has-text('मेरी देखभाल'), button:has-text('મારી સંભાળ'), button:has-text('My Care')").first();
    if (await myCareTab.isVisible()) {
      await myCareTab.click();
      await page.waitForTimeout(2000);
      // CAPTURE MY CARE SCREEN
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${lang.prefix}_my_care.png`), fullPage: true });
    }
  });
}
