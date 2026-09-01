import { test, expect } from '@playwright/test';

test.describe('Citizen Scheme Help Centre Flow E2E', () => {
  test('Complete flow: Scheme Detail -> Find Help Centre -> Location -> Help Centre Cards -> Facility Detail -> ASHA', async ({ page }) => {
    // Navigate to citizen mobile app
    await page.goto('http://localhost:3001');
    await page.waitForLoadState('networkidle');

    // Language selection
    const langBtn = page.locator('#btn-language-continue, button:has-text("Continue"), button:has-text("पुढे जा")').first();
    if (await langBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await langBtn.click();
    }

    // Continue as guest to enter Home
    const guestBtn = page.locator('#btn-entry-guest, button:has-text("Continue as Guest"), button:has-text("अतिथी म्हणून सुरू ठेवा")').first();
    await guestBtn.waitFor({ timeout: 10000 });
    await guestBtn.click();

    // Click Schemes Tab on bottom navigation
    const schemesTab = page.locator('button:has-text("Schemes"), button:has-text("योजना")').first();
    await schemesTab.waitFor({ timeout: 10000 });
    await schemesTab.click();

    // 1. Click Maternal category card
    const maternalCard = page.locator('#scheme-category-card-maternal_health, button:has-text("Maternal"), button:has-text("मातृ स्वास्थ्य")').first();
    await expect(maternalCard).toBeVisible({ timeout: 10000 });
    await maternalCard.click();

    // 2. Click Find Scheme Help Centre on PMMVY scheme card
    await page.waitForTimeout(500);
    const findHelpCentreBtn = page.locator('button:has-text("Find Scheme Help Centre"), button:has-text("योजना मदत केंद्र शोधा")').first();
    await expect(findHelpCentreBtn).toBeVisible({ timeout: 10000 });
    await findHelpCentreBtn.click();

    // 4. In Help Centres view, verify URL and scheme capabilities banner
    await expect(page).toHaveURL(/\/citizen\/schemes\/.*\/help-centres/);
    const capBanner = page.locator('text=Required Centre Capabilities')
      .or(page.locator('text=आवश्यक केंद्र सुविधा'));
    await expect(capBanner.first()).toBeVisible({ timeout: 5000 });

    // 5. Verify Location selection controls exist
    const gpsBtn = page.locator('#btn-use-current-location, button:has-text("GPS")').first();
    const registeredBtn = page.locator('#btn-use-registered-address, button:has-text("Registered Address")').first();
    const manualInput = page.locator('#input-manual-location, input[placeholder*="Village" i]').first();
    await expect(gpsBtn).toBeVisible();
    await expect(registeredBtn).toBeVisible();
    await expect(manualInput).toBeVisible();

    // 6. Test location selection (Registered Address)
    await registeredBtn.click();
    await page.waitForTimeout(500);

    // 7. Verify help centre cards are displayed with real directions link & action buttons
    const centreCards = page.locator('[id^="help-centre-card-"], button:has-text("View Details"), a[href*="google.com/maps"]');
    await expect(centreCards.first()).toBeVisible({ timeout: 10000 });

    // Check directions button on first card
    const firstDirectionsBtn = page.locator('[id^="btn-directions-"], a[href*="google.com/maps"]').first();
    await expect(firstDirectionsBtn).toBeVisible();
    const href = await firstDirectionsBtn.getAttribute('href');
    expect(href).toContain('google.com/maps/dir/?api=1');

    // 8. Click View Details on first card to navigate to Help Centre Detail view
    const firstDetailsBtn = page.locator('[id^="btn-view-details-"], button:has-text("View Details"), button:has-text("तपशील पहा")').first();
    await expect(firstDetailsBtn).toBeVisible();
    await firstDetailsBtn.click();

    // 9. Verify Help Centre Detail page
    await expect(page).toHaveURL(/\/citizen\/schemes\/.*\/help-centres\/.+/);
    const detailBanner = page.locator('text=Required Documents')
      .or(page.locator('text=केंद्रावर जाताना सोबत नेण्याची कागदपत्रे'))
      .or(page.locator('text=Final document and eligibility verification'));
    await expect(detailBanner.first()).toBeVisible({ timeout: 5000 });

    // 10. Test Ask ASHA for Help button
    const askAshaBtn = page.locator('#btn-detail-ask-asha, button:has-text("Ask ASHA"), button:has-text("आशा")').first();
    if (await askAshaBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await askAshaBtn.click();
    }
  });
});
