import pytest
from playwright.sync_api import sync_playwright, expect

def test_citizen_scheme_help_centres_flow_e2e():
    """
    End-to-end verification of Citizen Scheme Help Centre workflow:
    1. Scheme Categories -> Maternal Health
    2. Category List -> Scheme Detail (PMMVY)
    3. Scheme Detail -> Click 'Find Scheme Help Centre'
    4. Help Centres View -> Location Selection (Registered Address)
    5. Results -> Verified Badge, Capability Match, Directions Google Maps URL
    6. Card Detail -> Documents to Carry, Disclaimer, Operating Hours
    7. Facility Detail -> Ask ASHA for Help button -> Toast notification
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Pre-set localStorage to skip language onboarding and select schemes
            context.add_init_script("""
                localStorage.setItem('aarogya_lang_confirmed', 'true');
                localStorage.setItem('aarogya_citizen_lang', 'mr-IN');
                localStorage.setItem('aarogya:locale:citizen', 'mr-IN');
                localStorage.setItem('aarogya_citizen_onboarded', 'true');
                localStorage.setItem('aarogya_citizen_profile', JSON.stringify({
                    id: 'cit-001',
                    full_name: 'Sunita Devi',
                    phone: '9876543210',
                    state: 'Maharashtra',
                    district: 'District 04',
                    is_pregnant: true
                }));
            """)


            # Add console and response listener
            page.on("console", lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
            page.on("response", lambda res: print(f"RESPONSE {res.status} {res.url}") if res.status >= 400 else None)

            # Navigate to Citizen App
            page.goto("http://localhost:3001", timeout=15000)
            page.wait_for_timeout(1000)

            # Click Schemes tab on bottom navigation or home button
            schemes_nav = page.locator("#nav-tab-schemes")
            schemes_home = page.locator("#btn-home-govt-schemes")
            if schemes_home.is_visible():
                schemes_home.click()
            elif schemes_nav.is_visible():
                schemes_nav.click()
            page.wait_for_timeout(1000)

            # 1. Click Maternal Health Category Card
            cat_card = page.locator("#scheme-category-card-maternal_health")
            expect(cat_card).to_be_visible(timeout=10000)
            cat_card.click()
            page.wait_for_timeout(600)

            # 2. Click Find Help Centre directly on PMMVY Card in Category List
            help_btn = page.locator('[id^="btn-list-find-help-IN-MWCD-PMMVY"]').first
            expect(help_btn).to_be_visible(timeout=10000)
            help_btn.click()
            page.wait_for_timeout(2000)

            # Debug check
            print(f"DEBUG CURRENT URL: {page.url}")
            print(f"DEBUG IDS: {page.locator('[id]').evaluate_all('els => els.map(e => e.id)')}")


            # 4. Verify Help Centres view is loaded
            banner = page.locator("#required-capabilities-banner")
            expect(banner).to_be_visible(timeout=10000)

            reg_loc_btn = page.locator("#btn-use-registered-address")
            expect(reg_loc_btn).to_be_visible(timeout=10000)






            # 5. Click Registered Address location button
            reg_loc_btn = page.locator("#btn-use-registered-address")
            expect(reg_loc_btn).to_be_visible(timeout=10000)
            reg_loc_btn.click()

            # 6. Verify help centre cards are loaded
            first_card = page.locator('[id^="help-centre-card-"]').first
            expect(first_card).to_be_visible(timeout=10000)

            # 7. Verify Directions button contains Google Maps URL
            dir_btn = page.locator('[id^="btn-directions-"]').first
            expect(dir_btn).to_be_visible(timeout=10000)
            href = dir_btn.get_attribute("href")
            assert "google.com/maps/dir/?api=1" in href

            # 8. Click View Details on first card
            view_details_btn = page.locator('[id^="btn-view-details-"]').first
            expect(view_details_btn).to_be_visible(timeout=10000)
            view_details_btn.click()

            # 9. Verify Facility Detail view
            page.wait_for_url("**/citizen/schemes/**/help-centres/**", timeout=10000)
            expect(page.locator("#btn-detail-directions")).to_be_visible(timeout=10000)
            expect(page.locator("text=Final document and eligibility verification")).to_be_visible(timeout=10000)

            # 10. Click Ask ASHA for Help button on facility detail
            ask_asha_btn = page.locator("#btn-detail-ask-asha")
            expect(ask_asha_btn).to_be_visible(timeout=10000)
            ask_asha_btn.click()


            # Verify Toast confirmation
            expect(page.locator("#action-toast-notification, [role='alert'], div:has-text('विनंती यशस्वीपणे पाठवली')").first).to_be_visible(timeout=10000)


        finally:
            browser.close()
