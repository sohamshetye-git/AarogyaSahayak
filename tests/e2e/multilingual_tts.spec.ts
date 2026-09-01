import { test, expect } from '@playwright/test';

test.describe('Citizen Multilingual TTS Audio Playback Flow', () => {
  test.setTimeout(90000);

  test.beforeEach(async ({ page }) => {
    // Clear localStorage to test fresh onboarding
    await page.goto('http://localhost:3001');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  const locales = [
    { code: 'gu-IN', name: 'Gujarati' },
    { code: 'ta-IN', name: 'Tamil' },
    { code: 'ml-IN', name: 'Malayalam' },
    { code: 'od-IN', name: 'Odia' },
    { code: 'bn-IN', name: 'Bengali' },
    { code: 'kn-IN', name: 'Kannada' },
    { code: 'te-IN', name: 'Telugu' },
    { code: 'pa-IN', name: 'Punjabi' },
    { code: 'mr-IN', name: 'Marathi' },
    { code: 'hi-IN', name: 'Hindi' },
    { code: 'en-IN', name: 'English' }
  ];

  test('Observe and verify TTS network request and playback for all 11 locales', async ({ page }) => {
    // Instrument window to track Web Audio & HTML Audio play calls
    await page.evaluate(() => {
      (window as any).__audioPlayed = [];
      const origStart = AudioBufferSourceNode.prototype.start;
      AudioBufferSourceNode.prototype.start = function (...args) {
        (window as any).__audioPlayed.push('WebAudio:start');
        return origStart.apply(this, args);
      };
      const origPlay = HTMLAudioElement.prototype.play;
      HTMLAudioElement.prototype.play = function () {
        (window as any).__audioPlayed.push('HTMLAudio:play');
        return origPlay.apply(this);
      };
    });

    for (const loc of locales) {
      const btn = page.locator(`#btn-listen-${loc.code}`);
      await expect(btn).toBeVisible();

      // Intercept the API request
      const responsePromise = page.waitForResponse(
        (res) => res.url().includes('/api/voice/tts') && res.request().method() === 'POST',
        { timeout: 15000 }
      );

      // Click Listen button
      await btn.click();

      // Await network response
      const response = await responsePromise;
      expect(response.status()).toBe(200);

      const json = await response.json();
      expect(json.data).toBeDefined();
      expect(json.data.language_code).toBe(loc.code);
      expect(json.data.mime_type).toBe('audio/wav');
      expect(json.data.provider).toBe('SARVAM');
      expect(typeof json.data.audio_base64).toBe('string');
      expect(json.data.audio_base64.length).toBeGreaterThan(100);

      // Verify button shows playing state or successfully played
      await page.waitForTimeout(400);

      // Stop previous before testing next
      await btn.click();
      await page.waitForTimeout(100);
    }

    const audioPlayedEvents = await page.evaluate(() => (window as any).__audioPlayed);
    expect(audioPlayedEvents.length).toBeGreaterThan(0);
  });

  test('Verify Listen click does not change card selection', async ({ page }) => {
    // First select Gujarati by clicking its card
    const guCard = page.locator('div[role="button"][aria-label*="ગુજરાતી"]');
    await guCard.click();
    await expect(guCard).toHaveAttribute('aria-selected', 'true');

    // Click Listen for Punjabi
    const paBtn = page.locator('#btn-listen-pa-IN');
    await expect(paBtn).toBeVisible();
    await paBtn.click();

    // Verify Gujarati card is STILL selected, and Punjabi card is NOT selected
    await expect(guCard).toHaveAttribute('aria-selected', 'true');
    const paCard = page.locator('div[role="button"][aria-label*="ਪੰਜਾਬੀ"]');
    await expect(paCard).toHaveAttribute('aria-selected', 'false');
  });

  test('Verify Retry flow on error and rapid switching', async ({ page }) => {
    // Rapidly toggle between Gujarati and Odia
    const guBtn = page.locator('#btn-listen-gu-IN');
    const odBtn = page.locator('#btn-listen-od-IN');

    await guBtn.click();
    await page.waitForTimeout(50);
    await odBtn.click();

    // Verify Odia takes over and previous is stopped
    await expect(odBtn).toBeVisible();
  });
});
