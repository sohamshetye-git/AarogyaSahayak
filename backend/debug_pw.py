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
    page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))

    page.goto('http://localhost:3001')
    page.wait_for_timeout(1000)
    
    find_btn = page.locator("#btn-home-find-health-centre")
    print("Clicking #btn-home-find-health-centre...")
    find_btn.first.click()
    page.wait_for_timeout(1500)
    print("Page HTML after click:")
    print(page.content()[:1000])
    b.close()
