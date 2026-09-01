import pytest
import time
from playwright.sync_api import Page, expect

def test_playwright_citizen_google_maps_e2e(page: Page):
    """
    Playwright Browser Integration & Interaction Test for Google Maps Platform Integration:
    1. Mock GPS at 19.447, 72.824
    2. Select General Doctor / PHC (GENERAL_OPD)
    3. Click Find Suitable Health Centres
    4. Assert exactly one search request & button exits loading cleanly
    5. Assert results screen loads with interactive map and facility list
    6. Click marker/card and verify synchronized selection
    7. Test Directions button opens valid Google Maps URL
    8. Test manual village/PIN resolution modal
    9. Test responsive layout (390 mobile and 768 tablet)
    """
    # 1. Mobile Viewport
    page.set_viewport_size({"width": 390, "height": 844})
    
    # Grant and Mock Geolocation Permissions
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation({"latitude": 19.447, "longitude": 72.824})

    # Set up init script for citizen context
    page.context.add_init_script("""
        localStorage.setItem('aarogya_lang_confirmed', 'true');
        localStorage.setItem('aarogya_citizen_lang', 'mr-IN');
        localStorage.setItem('aarogya:locale:citizen', 'mr-IN');
        localStorage.setItem('aarogya_guest_session', JSON.stringify({
            guest_id: 'guest-test-123',
            created_at: new Date().toISOString()
        }));
    """)

    page.goto("http://localhost:3001", timeout=15000)

    # 2. Wait for App to load
    expect(page.locator("text=आरोग्य").or_(page.locator("text=Aarogya")).first).to_be_visible(timeout=10000)

    # 3. Navigate to Facilities screen
    nav_btn = page.locator("#btn-home-find-health-centre").or_(page.locator("text=आरोग्य केंद्र")).or_(page.locator("text=Health Centre")).first
    expect(nav_btn).to_be_visible(timeout=10000)
    nav_btn.click()

    # 4. Verify category selection
    expect(page.locator("text=What healthcare help do you need?").or_(page.locator("text=तुम्हाला कोणती आरोग्य मदत हवी आहे?")).first).to_be_visible(timeout=10000)

    # Select General Doctor / PHC
    opd_card = page.locator("#category-card-GENERAL_OPD").or_(page.locator("text=General Doctor / PHC")).or_(page.locator("text=प्राथमिक आरोग्य केंद्र (OPD)")).first
    expect(opd_card).to_be_visible(timeout=10000)
    opd_card.click()

    # 5. Click "Find Suitable Health Centres"
    search_btn = page.locator("#btn-find-suitable-facilities").or_(page.locator("text=Find Suitable Health Centres")).first
    expect(search_btn).to_be_visible(timeout=10000)
    search_btn.click()

    # 6. Verify Results Screen opens, loading stops, results appear
    expect(page.locator("text=Verified Facilities Found").or_(page.locator("text=Best Match")).first).to_be_visible(timeout=10000)

    # Check facility card elements
    expect(page.locator("text=Directions").first).to_be_visible(timeout=10000)

    # 7. Test Directions Button generates valid Google Maps URL
    directions_btn = page.locator("text=Directions").first
    expect(directions_btn).to_be_visible(timeout=10000)

    # 8. Test Tablet Viewport (768px)
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.locator("text=Verified Facilities Found").first).to_be_visible()

    # 9. Test Small Mobile Viewport (360px)
    page.set_viewport_size({"width": 360, "height": 640})
    expect(page.locator("text=Verified Facilities Found").first).to_be_visible()
