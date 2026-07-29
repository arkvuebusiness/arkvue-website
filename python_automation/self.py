import json
import subprocess
import time
from playwright.sync_api import sync_playwright

with open("arkvue_config.json", "r") as f:
    config = json.load(f)

browser_path = config["browser_path"]

# Launch the browser with remote debugging enabled + Instagram
subprocess.Popen([
    browser_path,
    "--remote-debugging-port=9222",
    "https://www.instagram.com/explore/",
])

time.sleep(3)  # give the browser process time to start (still fixed - unavoidable pre-connect)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.wait_for_load_state("domcontentloaded")

    SEARCH_KEYWORD = "testing"   # change this to search anything else

    for i in range(5):
        page.goto("https://www.instagram.com/explore/")
        page.wait_for_load_state("domcontentloaded")

        search_button = page.locator('div[role="button"]:has(svg[aria-label="Search"])').first
        search_button.wait_for(state="visible", timeout=10000)
        search_button.click()

        search_box = page.get_by_placeholder("Search")
        search_box.wait_for(state="visible", timeout=10000)
        search_box.fill(SEARCH_KEYWORD)

        # exclude sidebar/nav avatars (e.g. your own profile pic) - only match result rows
        avatar_links = page.locator(
            'a[role="link"]:not(nav a):not([role="navigation"] a):has(img[alt$="\'s profile picture"])'
        )

        # results stream in async - wait until at least 5 have rendered, not just the first
        for _ in range(20):
            if avatar_links.count() >= 5:
                break
            page.wait_for_timeout(300)

        # find your own profile link (the nav "Profile" icon) so we can exclude it below
        own_href = None
        own_profile_link = page.get_by_role("link", name="Profile")
        if own_profile_link.count() > 0:
            own_href = own_profile_link.first.get_attribute("href")

        raw_hrefs = avatar_links.evaluate_all("els => els.map(e => e.getAttribute('href'))")

        result_hrefs = []
        for h in raw_hrefs:
            if h is None or h == own_href:
                continue
            if h not in result_hrefs:   # dedupe repeated matches for the same profile
                result_hrefs.append(h)

        target_href = result_hrefs[i]
        page.locator(f'a[role="link"][href="{target_href}"]').first.click()

        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)  # let you see the profile before moving on