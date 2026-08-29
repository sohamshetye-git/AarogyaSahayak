import os
import pytest
from playwright.sync_api import Browser, expect

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

def test_admin_ai_privacy_no_pii_exposed(browser: Browser):
    context = browser.new_context()
    page = context.new_page()

    # 1. Login as District Health Officer (Admin)
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('District Health Officer (Admin)')")
    expect(page.locator("text=Privacy-Preserving Aggregate Mode Active")).to_be_visible()

    # 2. Inspect Admin Dashboard text content
    dashboard_text = page.content()
    assert "Sunita Devi" not in dashboard_text
    assert "9876543210" not in dashboard_text
    assert "12-3456-7890-1234" not in dashboard_text
    assert "Labetalol 100mg" not in dashboard_text

    # 3. Inspect System Health & AI Diagnostics Screen
    page.goto(f"{FRONTEND_URL}/admin/system-health")
    expect(page.locator("text=Integration Diagnostics & Service Health")).to_be_visible()
    
    health_text = page.content()
    assert "Sunita Devi" not in health_text
    assert "9876543210" not in health_text

    context.close()
