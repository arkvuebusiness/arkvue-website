#!/usr/bin/env python3
"""Find correct Explore selector on Instagram"""
import asyncio
from playwright.async_api import async_playwright

async def find_explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--remote-debugging-port=9222",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ]
        )
        
        cdp_browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = cdp_browser.contexts[0] if cdp_browser.contexts else await cdp_browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://instagram.com")
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        print("[TEST] Page loaded")
        
        # Find all links with "explore" in href or text
        links = await page.query_selector_all("a")
        print(f"[TEST] Found {len(links)} total links")
        
        for link in links:
            href = await link.get_attribute("href")
            text = await link.inner_text()
            role = await link.get_attribute("role")
            aria_label = await link.get_attribute("aria-label")
            if href and ("explore" in href.lower() or "explore" in text.lower() or 
                         (aria_label and "explore" in aria_label.lower())):
                print(f"  Found: href={href}, text='{text}', role={role}, aria-label={aria_label}")
        
        # Also check for nav elements
        print("\n[TEST] Checking nav/menus:")
        navs = await page.query_selector_all("nav a, [role='navigation'] a")
        for nav in navs:
            href = await nav.get_attribute("href")
            text = await nav.inner_text()
            if href and "explore" in href.lower():
                print(f"  Nav: href={href}, text='{text}'")
        
        await cdp_browser.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_explore())