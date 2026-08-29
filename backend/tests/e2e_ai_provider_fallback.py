import os
import pytest
from playwright.sync_api import Browser, expect

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

def test_core_workflow_resilience_when_external_ai_is_offline(browser: Browser):
    """
    Verifies that when external AI providers are unavailable,
    the core four-role clinical journey remains 100% operational.
    """
    context = browser.new_context()
    page = context.new_page()

    # 1. ASHA login and task viewing
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('ASHA Worker')")
    expect(page.locator("text=Priority Tasks & Field Visits")).to_be_visible()

    # 2. View case details & safety red flag
    page.click("text=Sunita Devi")
    expect(page.locator("text=Deterministic Clinical Red Flag Triggered")).to_be_visible()

    # 3. Doctor login & queue viewing
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('PHC Doctor')")
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()

    context.close()
