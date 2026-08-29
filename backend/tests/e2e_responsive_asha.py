import os
import pytest
from playwright.sync_api import Browser, expect
from app.database import SessionLocal

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@pytest.mark.parametrize("viewport_name,width,height", [
    ("mobile_360", 360, 640),
    ("mobile_390", 390, 844),
    ("tablet_768", 768, 1024),
    ("desktop_1440", 1440, 900)
])
def test_asha_responsive_viewports(browser: Browser, viewport_name: str, width: int, height: int):
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    # 1. Login
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('ASHA Worker')")
    expect(page.locator("text=Priority Tasks & Field Visits")).to_be_visible()

    # 2. Open Case
    page.goto(f"{FRONTEND_URL}/asha/cases/case-canonical-001")
    expect(page.locator("text=Case Ref:")).to_be_visible()

    # 3. Verify Timeline renders
    expect(page.locator("text=Longitudinal Case Timeline & Audit History")).to_be_visible()

    # 4. Visit Follow-ups tab
    page.goto(f"{FRONTEND_URL}/asha/followups")
    expect(page.locator("text=Doctor-Assigned Follow-up Tasks")).to_be_visible()

    # 5. Visit Offline Sync tab
    page.goto(f"{FRONTEND_URL}/asha/offline")
    expect(page.locator("text=Offline Queue & IndexedDB Sync")).to_be_visible()

    context.close()
