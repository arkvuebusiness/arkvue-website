import json
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

from playwright.sync_api import sync_playwright
from groq import Groq
import requests

CONFIG_FILE = "arkvue_config.json"

SYSTEM_PROMPT = "If the followers are greater than 30k, return yes. Otherwise return no."

stop_event = threading.Event()
worker_thread = None
llm_client = None  # created once config is loaded, inside run_automation


def append_to_sheet(script_url, username, followers):
    requests.post(script_url, json={"username": username, "followers": followers}, timeout=10)


def ask_llm(client, profile_info):
    user_prompt = (
        f"Username: {profile_info['username']}\n"
        f"Followers: {profile_info['followers']}\n"
        f"Posts: {profile_info['posts']}\n"
        f"Bio: {profile_info['bio']}"
    )
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        stream=False,
        stop=None,
    )
    return completion.choices[0].message.content.strip()


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
    # text_content() is used instead of inner_text() because the bio div uses CSS line-clamp
    # to visually truncate with "... more" - inner_text() respects that clamp, text_content() doesn't
    bio = ""
    bio_el = page.locator('span._ap3a').first
    if bio_el.count() > 0:
        bio = bio_el.text_content().strip()

    return {
        "username": username or "(unknown)",
        "followers": followers or "?",
        "posts": posts or "?",
        "bio": bio or "(no bio)",
    }


def _match(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None


def run_automation(keywords, log):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    browser_path = config["browser_path"]

    client = Groq(api_key=config["groq_api_key"])

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

        for keyword in keywords:
            log(f"\n=== Keyword: '{keyword}' ===")

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

                log(f"Searching for '{keyword}'...")
                search_box = page.get_by_placeholder("Search")
                search_box.wait_for(state="visible", timeout=10000)
                search_box.fill(keyword)

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

                log("  Asking LLM...")
                try:
                    decision = ask_llm(client, info)
                except Exception as e:
                    decision = f"(LLM error: {e})"
                log(f"  LLM Decision: {decision}")

                if decision.strip().lower().startswith("yes"):
                    script_url = config.get("google_script_url", "")
                    if script_url:
                        try:
                            append_to_sheet(script_url, info["username"], info["followers"])
                            log("  Added to Google Sheet.")
                        except Exception as e:
                            log(f"  Sheet error: {e}")
                    else:
                        log("  (no google_script_url set in Settings - skipped sheet)")

                log("-" * 40)

        log("Done - all keywords processed.")


def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def open_settings():
    config = load_config()

    win = tk.Toplevel(root)
    win.title("Settings")
    win.geometry("460x320")
    win.resizable(False, False)
    win.grab_set()  # modal - keep focus on this popup

    # --- Browser path ---
    tk.Label(win, text="Browser executable path:", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", padx=15, pady=(15, 0)
    )
    path_frame = tk.Frame(win)
    path_frame.pack(fill="x", padx=15, pady=5)

    path_var = tk.StringVar(value=config.get("browser_path", ""))
    path_entry = tk.Entry(path_frame, textvariable=path_var, font=("Consolas", 9))
    path_entry.pack(side="left", fill="x", expand=True)

    def browse_path():
        selected = filedialog.askopenfilename(title="Select browser executable")
        if selected:
            path_var.set(selected)

    tk.Button(path_frame, text="Browse...", command=browse_path).pack(side="left", padx=(8, 0))

    # --- LLM API key ---
    tk.Label(win, text="Groq LLM API key:", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", padx=15, pady=(15, 0)
    )
    key_var = tk.StringVar(value=config.get("groq_api_key", ""))
    key_entry = tk.Entry(win, textvariable=key_var, font=("Consolas", 9), show="*")
    key_entry.pack(fill="x", padx=15, pady=5)

    def toggle_key_visibility():
        key_entry.config(show="" if key_entry.cget("show") == "*" else "*")

    tk.Checkbutton(win, text="Show key", command=toggle_key_visibility).pack(anchor="w", padx=15)

    # --- Google Sheet webhook URL ---
    tk.Label(win, text="Google Apps Script URL:", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", padx=15, pady=(15, 0)
    )
    sheet_var = tk.StringVar(value=config.get("google_script_url", ""))
    sheet_entry = tk.Entry(win, textvariable=sheet_var, font=("Consolas", 9))
    sheet_entry.pack(fill="x", padx=15, pady=5)

    # --- Save ---
    def on_save():
        config["browser_path"] = path_var.get().strip()
        config["groq_api_key"] = key_var.get().strip()
        config["google_script_url"] = sheet_var.get().strip()
        save_config(config)
        messagebox.showinfo("Saved", "Settings saved to arkvue_config.json", parent=win)
        win.destroy()

    tk.Button(
        win, text="Save", font=("Segoe UI", 10, "bold"),
        bg="#5cb85c", fg="white", command=on_save,
    ).pack(pady=15)


def on_play():
    global worker_thread
    if worker_thread and worker_thread.is_alive():
        return  # already running

    raw = keyword_var.get().strip()
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    if not keywords:
        messagebox.showwarning("No keywords", "Enter at least one keyword (comma-separated) before pressing Play.")
        return

    stop_event.clear()
    play_button.config(text="Stop", bg="#d9534f")

    def target():
        try:
            run_automation(keywords, log)
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
root.geometry("520x480")

tk.Label(root, text="Keywords (comma-separated):", font=("Segoe UI", 10, "bold")).pack(
    anchor="w", padx=10, pady=(15, 0)
)
keyword_var = tk.StringVar()
keyword_entry = tk.Entry(root, textvariable=keyword_var, font=("Consolas", 10))
keyword_entry.pack(fill="x", padx=10, pady=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

play_button = tk.Button(
    button_frame, text="Play", font=("Segoe UI", 14, "bold"),
    bg="#5cb85c", fg="white", width=12, height=2,
    command=on_button_click,
)
play_button.pack(side="left", padx=5)

settings_button = tk.Button(
    button_frame, text="Settings", font=("Segoe UI", 11),
    width=10, height=2, command=open_settings,
)
settings_button.pack(side="left", padx=5)

log_box = scrolledtext.ScrolledText(root, width=62, height=16, font=("Consolas", 9))
log_box.pack(padx=10, pady=5)

root.mainloop()