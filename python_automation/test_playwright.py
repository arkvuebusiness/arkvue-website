#!/usr/bin/env python3
"""Test with existing browser on CDP port"""
import asyncio
from playwright.async_api import async_playwright

async def test_selectors():
    async with async_playwright() as p:
        # Connect to existing browser
        cdp_browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = cdp_browser.contexts[0] if cdp_browser.contexts else await cdp_browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Go to Instagram (should already be logged in)
        await page.goto("https://instagram.com")
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        print("[TEST] Page loaded")
        
        # Test Explore selector from config
        explore_sel = "a[href*='/explore/'][role='link']"
        try:
            await page.wait_for_selector(explore_sel, state="visible", timeout=10000)
            print("[TEST] Explore link found")
            await page.click(explore_sel)
            print("[TEST] Clicked Explore")
        except Exception as e:
            print(f"[TEST] Explore failed: {e}")
            await cdp_browser.close()
            return
        
        # Test search input on Explore page
        search_sel = "input[aria-label='Search input']"
        try:
            await page.wait_for_selector(search_sel, state="visible", timeout=15000)
            print("[TEST] Search input visible on Explore page")
            await page.wait_for_selector(search_sel, state="editable", timeout=10000)
            print("[TEST] Search input editable")
            await page.fill(search_sel, "testkeyword")
            print("[TEST] Filled search input")
            await page.press(search_sel, "Enter")
            print("[TEST] Pressed Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            print("[TEST] Results loaded")
        except Exception as e:
            print(f"[TEST] Search failed: {e}")
            return
        
        # Test profile container selector
        profile_sel = "div.x6s0dn4.x78zum5.xdt5ytf.x5yr21d.x1odjw0f.x1n2onr6.xh8yej3 a[href^='/'][role='link']"
        try:
            await page.wait_for_selector(profile_sel, state="attached", timeout=10000)
            links = await page.query_selector_all(profile_sel)
            print(f"[TEST] Found {len(links)} profile links")
            for i, link in enumerate(links[:5]):
                href = await link.get_attribute("href")
                print(f"  Profile {i+1}: {href}")
        except Exception as e:
            print(f"[TEST] Profile links failed: {e}")
        
        await cdp_browser.close()

if __name__ == "__main__":
    asyncio.run(test_selectors())