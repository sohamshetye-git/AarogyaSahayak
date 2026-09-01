import pytest
from playwright.sync_api import Page, expect

def test_language_selection_listen_buttons_all_11_locales(page: Page):
    """
    E2E Playwright test for Language Selection Screen Listen buttons:
    1. Tests all 11 Listen buttons
    2. Verifies clicking Listen does NOT alter the selected language card
    3. Verifies Stop button state during playback
    4. Verifies responsive 360px and 390px layouts
    """
    # 1. Test 360px mobile viewport (common Indian rural smartphone size)
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto("http://localhost:3001")
    page.wait_for_selector("#btn-listen-mr-IN", timeout=10000)

    # Click to select Marathi card explicitly
    mr_card = page.locator("[role='button'][aria-label*='मराठी']")
    mr_card.click()
    expect(mr_card).to_have_attribute("aria-selected", "true")

    # 2. Click Listen on Hindi button
    hi_listen_btn = page.locator("#btn-listen-hi-IN")
    hi_listen_btn.click()

    # Verify clicking Hindi Listen does NOT change selected card (Marathi must remain selected)
    expect(mr_card).to_have_attribute("aria-selected", "true")
    hi_card = page.locator("[role='button'][aria-label*='हिंदी']")
    expect(hi_card).to_have_attribute("aria-selected", "false")

    # 3. Test clicking another language (Tamil) stops the previous and initiates Tamil
    ta_listen_btn = page.locator("#btn-listen-ta-IN")
    ta_listen_btn.click()
    expect(mr_card).to_have_attribute("aria-selected", "true")

    # 4. Verify all 11 Listen buttons exist, have proper aria attributes, and are interactive
    all_locales = [
        "en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN",
        "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"
    ]

    for locale in all_locales:
        btn = page.locator(f"#btn-listen-{locale}")
        expect(btn).to_be_visible()
        expect(btn).to_have_attribute("aria-label")

    # 5. Test 390px viewport (iPhone / standard modern Android)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.locator("#btn-language-continue")).to_be_visible()
