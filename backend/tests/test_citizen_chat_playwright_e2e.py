import os
import time
from playwright.sync_api import sync_playwright
import pytest

def test_citizen_voice_chat_multilingual_ui():
    os.makedirs("backend/tests/screenshots", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            permissions=["microphone"]
        )
        page = context.new_page()

        # Navigate to citizen app
        page.goto("http://localhost:3001", wait_until="networkidle")

        # Handle onboarding language selection if visible
        marathi_btn = page.locator("button:has-text('मराठी')")
        if marathi_btn.is_visible():
            marathi_btn.click()
            page.wait_for_timeout(500)

        # Confirm language continue button if shown
        continue_btn = page.locator("button:has-text('पुढे चला'), button:has-text('Continue'), button:has-text('पुढे')")
        if continue_btn.is_visible():
            continue_btn.click()
            page.wait_for_timeout(1000)

        # Verify on Home or Open Assistant
        type_btn = page.locator("button:has-text('टाइप करा'), button:has-text('Type')").first
        if type_btn.is_visible():
            type_btn.click()
            page.wait_for_timeout(1000)
        else:
            speak_btn = page.locator("button:has-text('बोलून सांगा'), button:has-text('Speak')").first
            if speak_btn.is_visible():
                speak_btn.click()
                page.wait_for_timeout(1000)

        # Check Assistant Chat UI Header
        emergency_btn = page.locator("header button:has-text('108')").first
        emergency_btn.wait_for(timeout=5000)
        assert emergency_btn.is_visible()

        # Check WhatsApp-style sticky composer
        composer_input = page.locator("footer input").first
        composer_input.wait_for(timeout=5000)
        assert composer_input.is_visible()

        # 1. Turn 1: Initial fever message
        composer_input.fill("मला दोन दिवसांपासून ताप आहे आणि अशक्तपणा वाटतोय")
        send_btn = page.locator("footer button[aria-label='Send message']").first
        send_btn.click()
        page.wait_for_timeout(1500)

        # Check responsive viewports
        for vp in [
            {"width": 360, "height": 640},
            {"width": 390, "height": 844},
            {"width": 768, "height": 1024},
            {"width": 1440, "height": 900}
        ]:
            page.set_viewport_size(vp)
            page.wait_for_timeout(200)
            assert composer_input.is_visible()

        # Take screenshot for visual verification
        page.screenshot(path="backend/tests/screenshots/citizen_chat_journey_verified.png")
        browser.close()
