import requests
import re
import time

def monitor():
    print("Monitoring Vercel Healthcare Portal deployment...")
    for i in range(24):
        try:
            r = requests.get("https://aarogya-sahayak-healthcare-portal.vercel.app", timeout=15)
            js = re.findall(r'/assets/[^"\']+\.js', r.text)
            print(f"Attempt {i+1}: status={r.status_code}, bundle={js}")
            if js:
                js_url = "https://aarogya-sahayak-healthcare-portal.vercel.app" + js[0]
                js_content = requests.get(js_url, timeout=15).text
                # Check for unique string or code present in our new commit
                if "isChatPollingRef" in js_content or "mergeMessagesCanonical" in js_content or "activeChatReqRef" in js_content or "dmsg-" in js_content:
                    print(f"SUCCESS: New doctor-chat synchronization logic confirmed in bundle {js[0]}!")
                    return True
        except Exception as e:
            print(f"Attempt {i+1} error:", e)
        time.sleep(8)
    return False

if __name__ == "__main__":
    monitor()
