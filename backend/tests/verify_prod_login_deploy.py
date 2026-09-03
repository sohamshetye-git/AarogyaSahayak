import requests
import re
import time
import sys

def verify():
    print("Checking Vercel Production deployment for commit c279d5b...")
    for i in range(25):
        try:
            # Bypass any cache by querying index.html
            r = requests.get("https://aarogya-sahayak-healthcare-portal.vercel.app/login", headers={"Cache-Control": "no-cache"}, timeout=15)
            js_bundles = re.findall(r'/assets/[^"\']+\.js', r.text)
            print(f"[{i+1}/25] Status: {r.status_code}, Found JS Bundles: {js_bundles}")
            
            if js_bundles:
                js_url = "https://aarogya-sahayak-healthcare-portal.vercel.app" + js_bundles[0]
                js_content = requests.get(js_url, headers={"Cache-Control": "no-cache"}, timeout=15).text
                
                # Check for unique strings introduced in this exact redesign
                has_sign_in_securely = "Sign In Securely" in js_content
                has_auth_access_footer = "Authorized access only • Secure role-based healthcare portal" in js_content
                has_clinical_intel_sub = "Healthcare & Clinical Intelligence Portal" in js_content
                has_clean_grid = "role-col-asha" in js_content and "role-col-doctor" in js_content
                
                # Check that obsolete banners/demo wording are absent
                no_old_hackathon = "Hackathon Demo Accounts" not in js_content
                no_old_1click = "1-Click Login" not in js_content
                no_brand_trust = "brand-trust-points" not in js_content
                
                print(f"  - 'Sign In Securely': {has_sign_in_securely}")
                print(f"  - 'Authorized access only...': {has_auth_access_footer}")
                print(f"  - 'Healthcare & Clinical Intelligence Portal': {has_clinical_intel_sub}")
                print(f"  - Clean role grid: {has_clean_grid}")
                print(f"  - Obsolete wording absent: {no_old_hackathon and no_old_1click and no_brand_trust}")
                
                if has_sign_in_securely and has_auth_access_footer and has_clinical_intel_sub and has_clean_grid and no_old_hackathon:
                    print("\n>>> PRODUCTION VERCEL DEPLOYMENT CONFIRMED WITH NEW LOGIN CARD! <<<")
                    return True
        except Exception as e:
            print(f"[{i+1}/25] Error: {e}")
        time.sleep(6)
    return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
