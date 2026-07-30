import json
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

from playwright.sync_api import sync_playwright

SEARCH_KEYWORD = "testing"   # change this to search anything else

stop_event = threading.Event()
worker_thread = None


def extract_profile_info(page):
    # username sits inside the profile's <h2> - h2 maps to accessibility role "heading" level 2
    username = ""
    heading = page.get_by_role("heading", level=2)
    if heading.count() > 0:
        username = heading.first.inner_text().strip()

    # posts/followers/following are plain text inside <header> - regex is more robust
    # here than chasing the auto-generated class names
    header_text = page.locator("header").first.inner_text()
    posts = _match(r'([\d,\.]+\s*[KkMm]?)\s*posts', header_text)
    followers = _match(r'([\d,\.]+\s*[KkMm]?)\s*followers', header_text)

    # the bio text uses Instagram's stable "_ap3a" class (not the auto-generated x... ones)
    bio = ""
    bio_el = page.locator('span._ap3a').first
    if bio_el.count() > 0:
        bio = bio_el.inner_text().strip()

    return {
        "username": username or "(unknown)",
        "followers": followers or "?",
        "posts": posts or "?",
        "bio": bio or "(no bio)",
    }


def _match(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None


def run_automation(log):
    with open("arkvue_config.json", "r") as f:
        config = json.load(f)
    browser_path = config["browser_path"]

    log("Launching browser...")
    subprocess.Popen([
        browser_path,
        "--remote-debugging-port=9222",
        "https://www.instagram.com/explore/",
    ])
    time.sleep(3)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        page.wait_for_load_state("domcontentloaded")

        for i in range(5):
            if stop_event.is_set():
                log("Stopped.")
                return

            log("Opening explore page...")
            page.goto("https://www.instagram.com/explore/")
            page.wait_for_load_state("domcontentloaded")

            log("Clicking search box...")
            search_button = page.locator('div[role="button"]:has(svg[aria-label="Search"])').first
            search_button.wait_for(state="visible", timeout=10000)
            search_button.click()

            log(f"Searching for '{SEARCH_KEYWORD}'...")
            search_box = page.get_by_placeholder("Search")
            search_box.wait_for(state="visible", timeout=10000)
            search_box.fill(SEARCH_KEYWORD)

            avatar_links = page.locator(
                'a[role="link"]:not(nav a):not([role="navigation"] a):has(img[alt$="\'s profile picture"])'
            )
            for _ in range(20):
                if avatar_links.count() >= 5:
                    break
                page.wait_for_timeout(300)

            own_href = None
            own_profile_link = page.get_by_role("link", name="Profile")
            if own_profile_link.count() > 0:
                own_href = own_profile_link.first.get_attribute("href")

            raw_hrefs = avatar_links.evaluate_all("els => els.map(e => e.getAttribute('href'))")
            result_hrefs = []
            for h in raw_hrefs:
                if h is None or h == own_href:
                    continue
                if h not in result_hrefs:
                    result_hrefs.append(h)

            target_href = result_hrefs[i]
            log(f"Opening profile {i + 1}: {target_href}")
            page.locator(f'a[role="link"][href="{target_href}"]').first.click()

            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)

            info = extract_profile_info(page)
            log(f"  Username : {info['username']}")
            log(f"  Followers: {info['followers']}")
            log(f"  Posts    : {info['posts']}")
            log(f"  Bio      : {info['bio']}")
            log("-" * 40)

        log("Done - all 5 profiles opened.")


def on_play():
    global worker_thread
    if worker_thread and worker_thread.is_alive():
        return  # already running

    stop_event.clear()
    play_button.config(text="Stop", bg="#d9534f")

    def target():
        try:
            run_automation(log)
        except Exception as e:
            log(f"Error: {e}")
        finally:
            play_button.config(text="Play", bg="#5cb85c")

    worker_thread = threading.Thread(target=target, daemon=True)
    worker_thread.start()


def on_stop():
    stop_event.set()
    log("Stopping after current step...")


def on_button_click():
    if worker_thread and worker_thread.is_alive():
        on_stop()
    else:
        on_play()


def log(message):
    def update():
        log_box.insert(tk.END, message + "\n")
        log_box.see(tk.END)
    root.after(0, update)


root = tk.Tk()
root.title("Instagram Profile Opener")
root.geometry("520x420")

play_button = tk.Button(
    root, text="Play", font=("Segoe UI", 14, "bold"),
    bg="#5cb85c", fg="white", width=12, height=2,
    command=on_button_click,
)
play_button.pack(pady=15)

log_box = scrolledtext.ScrolledText(root, width=62, height=16, font=("Consolas", 9))
log_box.pack(padx=10, pady=5)

root.mainloop()