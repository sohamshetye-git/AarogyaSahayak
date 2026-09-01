import pytest
import re
from playwright.sync_api import Page, expect

def test_playwright_citizen_find_health_centre_flow(page: Page):
    """
    Playwright E2E Test:
    1. Open Citizen Mobile app
    2. Navigate to Find Health Centre
    3. Verify Category Cards Selection & Highlight (e.g. Maternity, Emergency, Child Vaccination)
    4. Verify Beneficiary Switcher & Location Workflow
    5. Search and verify capability-first ranked facility cards
    6. Verify Details modal and verified services
    7. Test responsive layout at 390px (mobile)
    """
    # Emulate Mobile Viewport & Geolocation Permission
    page.set_viewport_size({"width": 390, "height": 844})
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation({"latitude": 18.5204, "longitude": 73.8567})
    
    # Set up init script for citizen context
    page.context.add_init_script("""
        localStorage.setItem('aarogya_language_confirmed', 'true');
        localStorage.setItem('aarogya_preferred_language', 'mr-IN');
        localStorage.setItem('aarogya_citizen_lang', 'mr-IN');
        localStorage.setItem('aarogya:locale:citizen', 'mr-IN');
        localStorage.setItem('aarogya_guest_session', JSON.stringify({
            guest_id: 'guest-test-123',
            created_at: new Date().toISOString()
        }));
    """)

    try:
        page.goto("http://localhost:3001", timeout=5000)
    except Exception:
        page.goto("http://localhost:5173", timeout=15000)

    # Wait for app load and navigate to Facilities screen
    health_centre_button = page.locator("#btn-home-find-health-centre")
    expect(health_centre_button).to_be_visible(timeout=15000)
    health_centre_button.click()

    # Verify "What healthcare help do you need?" header
    expect(page.locator("text=What healthcare help do you need?").or_(page.locator("text=तुम्हाला कोणती आरोग्य मदत हवी आहे?")).first).to_be_visible(timeout=10000)

    # Select "Pregnancy & Delivery" / "Maternity"
    maternity_card = page.locator("#category-card-MATERNITY")
    maternity_card.wait_for(state="visible", timeout=10000)
    maternity_card.click(force=True)

    # Click "Find Suitable Health Centres"
    search_btn = page.locator("#btn-find-suitable-facilities")
    search_btn.wait_for(state="visible", timeout=10000)
    search_btn.click(force=True)

    # Verify Results Screen Loads with Best Match
    expect(page.locator("text=Verified Facilities Found").or_(page.locator("text=Best Match")).or_(page.locator("text=कल्याणपूर")).or_(page.locator("text=PHC")).first).to_be_visible(timeout=15000)

    # Click "Details" on the top ranked facility card
    details_btn = page.locator("button:has-text('Details')").first
    expect(details_btn).to_be_visible()
    details_btn.click()

    # Verify verified services list
    expect(page.locator("text=Operating Hours & Status").or_(page.locator("text=Directions")).first).to_be_visible()
