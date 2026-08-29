import { test, expect } from '@playwright/test';

test.describe('Citizen Scheme Help Centre Flow E2E', () => {
  test('Complete flow: Scheme Detail -> Find Help Centre -> Location -> Help Centre Cards -> Facility Detail -> ASHA', async ({ page }) => {
    // Navigate to citizen schemes page
    await page.goto('http://localhost:3001/citizen/schemes');
    await page.waitForLoadState('networkidle');

    // 1. Click Maternal category card
    const maternalCard = page.locator('#scheme-category-card-maternal_health');
    await expect(maternalCard).toBeVisible();
    await maternalCard.click();

    // 2. Expect category schemes list and click on PMMVY scheme
    await page.waitForTimeout(500);
    const pmmvyCard = page.locator('[id^="scheme-item-IN-MWCD-PMMVY"]');
    await expect(pmmvyCard).toBeVisible();
    await pmmvyCard.click();

    // 3. In Scheme Detail, verify Find Help Centre button is visible & clickable
    await page.waitForTimeout(500);
    const findHelpCentreBtn = page.locator('#btn-scheme-detail-find-help-centre');
    await expect(findHelpCentreBtn).toBeVisible();
    await findHelpCentreBtn.click();

    // 4. In Help Centres view, verify URL and scheme capabilities banner
    await expect(page).toHaveURL(/\/citizen\/schemes\/.*\/help-centres/);
    await expect(page.locator('text=आवश्यक केंद्र सुविधा')).toBeVisible();

    // 5. Verify Location selection controls exist
    const gpsBtn = page.locator('#btn-use-current-location');
    const registeredBtn = page.locator('#btn-use-registered-address');
    const manualInput = page.locator('#input-manual-location');
    await expect(gpsBtn).toBeVisible();
    await expect(registeredBtn).toBeVisible();
    await expect(manualInput).toBeVisible();

    // 6. Test location selection (Registered Address)
    await registeredBtn.click();
    await page.waitForTimeout(500);

    // 7. Verify help centre cards are displayed with real directions link & action buttons
    const centreCards = page.locator('[id^="help-centre-card-"]');
    await expect(centreCards.first()).toBeVisible();

    // Check directions button on first card
    const firstDirectionsBtn = page.locator('[id^="btn-directions-"]').first();
    await expect(firstDirectionsBtn).toBeVisible();
    const href = await firstDirectionsBtn.getAttribute('href');
    expect(href).toContain('google.com/maps/dir/?api=1');

    // 8. Click View Details on first card to navigate to Help Centre Detail view
    const firstDetailsBtn = page.locator('[id^="btn-view-details-"]').first();
    await expect(firstDetailsBtn).toBeVisible();
    await firstDetailsBtn.click();

    // 9. Verify Help Centre Detail page
    await expect(page).toHaveURL(/\/citizen\/schemes\/.*\/help-centres\/.+/);
    await expect(page.locator('text=केंद्रावर जाताना सोबत नेण्याची कागदपत्रे')).toBeVisible();
    await expect(page.locator('text=Final document and eligibility verification')).toBeVisible();

    // 10. Test Ask ASHA for Help button
    const askAshaBtn = page.locator('#btn-detail-ask-asha');
    await expect(askAshaBtn).toBeVisible();
    await askAshaBtn.click();

    // Verify toast notification appears
    await expect(page.locator('text=आशा')).toBeVisible();
  });
});
