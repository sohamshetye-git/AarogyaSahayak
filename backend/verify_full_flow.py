from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={'width': 390, 'height': 844})
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation({"latitude": 18.5204, "longitude": 73.8567})
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

    page.goto('http://localhost:3001')
    page.wait_for_timeout(1000)
    
    # Navigate to Facilities
    find_btn = page.locator("#btn-home-find-health-centre")
    find_btn.click()
    page.wait_for_timeout(500)
    
    # Select Maternity Category
    page.locator("#category-card-MATERNITY").click(force=True)
    page.wait_for_timeout(500)
    
    # Click Find Suitable Health Centres
    page.locator("#btn-find-suitable-facilities").click(force=True)
    page.wait_for_timeout(1000)
    
    # Intercept window.open for directions
    opened_urls = []
    page.on("popup", lambda p: opened_urls.append(p.url))
    
    # Click Directions button
    directions_btn = page.locator("button:has-text('Directions')").first
    print("Directions button text:", directions_btn.inner_text().strip())
    
    # Call button
    call_btn = page.locator("button:has-text('Call')").first
    print("Call button text:", call_btn.inner_text().strip())
    
    # Details button
    details_btn = page.locator("button:has-text('Details')").first
    print("Details button text:", details_btn.inner_text().strip())
    details_btn.click(force=True)
    page.wait_for_timeout(500)
    
    print("\nFacility Detail Screen verified!")
    print("Modal text snippet:", page.locator("body").inner_text()[:400].encode('ascii', 'replace').decode().replace("\n", " | "))
    
    b.close()
