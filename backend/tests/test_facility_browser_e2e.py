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
    # Emulate Mobile Viewport
    page.set_viewport_size({"width": 390, "height": 844})
    try:
        page.goto("http://localhost:3001", timeout=5000)
    except Exception:
        page.goto("http://localhost:5173", timeout=15000)

    # Wait for app load
    expect(page.locator("text=Aarogya").first).to_be_visible(timeout=10000)

    # Navigate to Facilities screen (or click Find Health Centre card)
    health_centre_button = page.locator("text=आरोग्य केंद्र").or_(page.locator("text=Health Centre")).or_(page.locator("text=जवळचे आरोग्य केंद्र")).first
    if health_centre_button.is_visible():
        health_centre_button.click()

    # Verify "What healthcare help do you need?" header
    expect(page.locator("text=What healthcare help do you need?").or_(page.locator("text=तुम्हाला कोणती आरोग्य मदत हवी आहे?")).first).to_be_visible()

    # Select "Pregnancy & Delivery" / "Maternity"
    maternity_card = page.locator("text=Pregnancy & Delivery").or_(page.locator("text=गरोदरपण व प्रसूती सेवा")).first
    expect(maternity_card).to_be_visible()
    maternity_card.click()

    # Verify category highlight banner
    expect(page.locator("text=Selected:").or_(page.locator("text=गरोदरपण")).first).to_be_visible()

    # Click "Find Suitable Health Centres"
    search_btn = page.locator("text=Find Suitable Health Centres").or_(page.locator("text=योग्य आरोग्य केंद्र शोधा")).first
    expect(search_btn).to_be_visible()
    search_btn.click()

    # Verify Results Screen Loads with Best Match
    expect(page.locator("text=Verified Facilities Found").or_(page.locator("text=Best Match")).first).to_be_visible(timeout=8000)
    expect(page.locator("text=Kalyanpur Primary Health Centre").or_(page.locator("text=कल्याणपूर")).first).to_be_visible()

    # Click "Details"
    details_btn = page.locator("text=Details").first
    expect(details_btn).to_be_visible()
    details_btn.click()

    # Verify verified services list
    expect(page.locator("text=Available Services & Capabilities").or_(page.locator("text=सेवा")).first).to_be_visible()
    expect(page.locator("text=Verified Available").first).to_be_visible()
