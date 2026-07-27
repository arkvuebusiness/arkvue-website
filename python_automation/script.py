import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import json
import os
import threading
import subprocess
import time
from playwright.sync_api import sync_playwright

CONFIG_FILE = "arkvue_config.json"

play_running = {"active": False, "thread": None, "stop_flag": False, "browser_process": None, "playwright_browser": None}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "system_prompt": "You are an AI assistant designed to help with automation tasks...\n\nBe precise, efficient, and safe in all operations.",
        "browser_path": "",
        "selectors": {
            "explore": "a[href='/explore/']",
            "search_input": "input[placeholder='Search']",
            "profile_1": "a[href*='/'][role='link']:nth-of-type(1)",
            "profile_2": "a[href*='/'][role='link']:nth-of-type(2)",
            "profile_3": "a[href*='/'][role='link']:nth-of-type(3)",
            "profile_4": "a[href*='/'][role='link']:nth-of-type(4)",
            "profile_5": "a[href*='/'][role='link']:nth-of-type(5)"
        },
        "delays": {"click": 500, "type": 100, "search_wait": 2000, "profile_wait": 2000}
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

config = load_config()

live_coords = {"x": 0, "y": 0}

def update_mouse_coords():
    try:
        import pyautogui
        x, y = pyautogui.position()
        live_coords["x"] = x
        live_coords["y"] = y
        mouse_label.config(text=f"Mouse: ({x}, {y})")
    except:
        pass
    root.after(50, update_mouse_coords)

def show_config():
    config_win = tk.Toplevel(root)
    config_win.title("Configuration")
    config_win.geometry("600x700")
    config_win.resizable(False, False)
    config_win.transient(root)
    config_win.grab_set()
    config_win.configure(bg="#ECF0F1")

    canvas = tk.Canvas(config_win, bg="#ECF0F1", highlightthickness=0)
    scrollbar = tk.Scrollbar(config_win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#ECF0F1")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _unbind_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", _unbind_mousewheel)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")

    tk.Label(scrollable_frame, text="Configuration", font=("Segoe UI", 14, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=15)

    # Browser Path
    browser_frame = tk.Frame(scrollable_frame, bg="#ECF0F1")
    browser_frame.pack(pady=5, fill="x", padx=20)

    tk.Label(browser_frame, text="Browser Executable:", font=("Segoe UI", 10, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(side="left", padx=(0, 10))

    browser_path_var = tk.StringVar(value=config.get("browser_path", ""))

    def select_browser():
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Select Browser Executable", filetypes=[("Executable", "*"), ("All files", "*.*")])
        if path:
            browser_path_var.set(path)
            config["browser_path"] = path
            save_config(config)

    tk.Button(browser_frame, text="📁 Browse", font=("Segoe UI", 9, "bold"), bg="#3498DB", fg="white", relief="flat", cursor="hand2", padx=15, pady=3, command=select_browser).pack(side="right", padx=(10, 0))
    tk.Entry(browser_frame, textvariable=browser_path_var, font=("Segoe UI", 10), relief="flat", bg="#F8F9FA", fg="#2C3E50").pack(side="left", fill="x", expand=True, padx=(0, 10))

    # Selectors
    tk.Label(scrollable_frame, text="CSS Selectors", font=("Segoe UI", 11, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=10)

    selectors = config.get("selectors", {})
    selector_vars = {}

    selector_labels = {
        "explore": "Explore Page Link",
        "search_input": "Search Input Field",
        "profile_1": "Profile 1 Selector",
        "profile_2": "Profile 2 Selector",
        "profile_3": "Profile 3 Selector",
        "profile_4": "Profile 4 Selector",
        "profile_5": "Profile 5 Selector"
    }

    for key, label_text in selector_labels.items():
        frame = tk.Frame(scrollable_frame, bg="#ECF0F1")
        frame.pack(pady=4, fill="x", padx=20)
        tk.Label(frame, text=label_text + ":", font=("Segoe UI", 9, "bold"), bg="#ECF0F1", fg="#2C3E50", width=22, anchor="w").pack(side="left")
        var = tk.StringVar(value=selectors.get(key, ""))
        selector_vars[key] = var
        tk.Entry(frame, textvariable=var, font=("Segoe UI", 9), relief="flat", bg="#F8F9FA", fg="#2C3E50").pack(side="left", fill="x", expand=True, padx=(10, 0))

    # Delays
    tk.Label(scrollable_frame, text="Delays (ms)", font=("Segoe UI", 11, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=10)

    delays = config.get("delays", {})
    delay_vars = {}
    delay_labels = {"click": "Click Delay", "type": "Type Delay", "search_wait": "Search Wait", "profile_wait": "Profile Wait"}

    for key, label_text in delay_labels.items():
        frame = tk.Frame(scrollable_frame, bg="#ECF0F1")
        frame.pack(pady=4, fill="x", padx=20)
        tk.Label(frame, text=label_text + ":", font=("Segoe UI", 9, "bold"), bg="#ECF0F1", fg="#2C3E50", width=22, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(delays.get(key, 500)))
        delay_vars[key] = var
        tk.Entry(frame, textvariable=var, font=("Segoe UI", 9), relief="flat", bg="#F8F9FA", fg="#2C3E50", width=10).pack(side="left", padx=(10, 0))

    def save_and_close():
        config["browser_path"] = browser_path_var.get()
        config["selectors"] = {k: v.get() for k, v in selector_vars.items()}
        config["delays"] = {k: int(v.get()) for k, v in delay_vars.items()}
        save_config(config)
        config_win.destroy()

    tk.Button(scrollable_frame, text="Save & Close", font=("Segoe UI", 10, "bold"), bg="#27AE60", fg="white", relief="flat", cursor="hand2", padx=20, pady=5, command=save_and_close).pack(pady=20)

def show_system_prompt():
    prompt_win = tk.Toplevel(root)
    prompt_win.title("System Prompt")
    prompt_win.geometry("500x400")
    prompt_win.resizable(False, False)
    prompt_win.transient(root)
    prompt_win.grab_set()

    tk.Label(prompt_win, text="System Prompt", font=("Segoe UI", 12, "bold"), fg="#2C3E50").pack(pady=10)

    text_area = scrolledtext.ScrolledText(prompt_win, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#F8F9FA", fg="#2C3E50")
    text_area.pack(fill="both", expand=True, padx=15, pady=10)
    text_area.insert("1.0", config.get("system_prompt", ""))

    def save_prompt():
        config["system_prompt"] = text_area.get("1.0", "end-1c")
        save_config(config)
        prompt_win.destroy()

    tk.Button(prompt_win, text="Save", font=("Segoe UI", 10, "bold"), bg="#27AE60", fg="white", relief="flat", cursor="hand2", padx=20, pady=5, command=save_prompt).pack(pady=10)

def play_script():
    global play_running
    import time

    if play_running["active"]:
        play_running["stop_flag"] = True
        play_btn.config(text="▶", bg="#27AE60")
        play_running["active"] = False
        status_label.config(text="Status: Stopped by user")
        return

    keyword = search_entry.get().strip()
    browser_path = config.get("browser_path", "")
    selectors = config.get("selectors", {})
    delays = config.get("delays", {})

    if not keyword or keyword == "Enter keywords...":
        messagebox.showwarning("Empty Keyword", "Keyword box is empty. Please enter a keyword.")
        status_label.config(text="Status: Keyword box is empty")
        return

    if not browser_path or not os.path.exists(browser_path):
        messagebox.showwarning("Browser Not Set", "Please set a valid browser executable path in Configuration.")
        status_label.config(text="Status: Browser path not configured")
        return

    required_selectors = ["explore", "search_input"]
    missing = [s for s in required_selectors if not selectors.get(s)]
    if missing:
        messagebox.showwarning("Missing Selectors", f"Please configure selectors: {', '.join(missing)}")
        status_label.config(text=f"Status: Missing selectors")
        return

    # Launch browser
    try:
        import subprocess
        browser_process = subprocess.Popen([
            browser_path, 
            "--remote-debugging-port=9222",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "https://instagram.com"
        ])
        play_running["browser_process"] = browser_process
        status_label.config(text="Status: Launched browser...")
        root.update()
        time.sleep(8)  # Wait longer for browser to fully start
    except Exception as e:
        messagebox.showwarning("Browser Launch Failed", f"Could not launch browser: {e}")
        play_running["browser_process"] = None
        return

    play_running["active"] = True
    play_running["stop_flag"] = False
    play_btn.config(text="■", bg="#E74C3C")
    status_label.config(text="Status: Running...")

    def run_automation():
        with sync_playwright() as p:
            try:
                # Connect with retries
                browser = None
                for attempt in range(5):
                    try:
                        status_label.config(text=f"Status: Connecting to CDP (attempt {attempt+1}/5)...")
                        root.update()
                        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                        break
                    except Exception as e:
                        if attempt == 4:
                            raise
                        time.sleep(2)
                
                play_running["playwright_browser"] = browser
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                status_label.config(text=f"Status: Got page, waiting for load...")
                root.update()
                page.wait_for_load_state("domcontentloaded", timeout=30000)

                def check_stop():
                    if play_running["stop_flag"]:
                        return True
                    return False

                # Click Explore
                if check_stop():
                    finish_playback()
                    return
                status_label.config(text=f"Status: Clicking Explore...")
                root.update()
                page.click(selectors["explore"], timeout=10000)
                status_label.config(text=f"Status: Waiting for Explore page...")
                root.update()
                # Wait for search input to appear (indicates Explore page loaded)
                page.wait_for_selector(selectors["search_input"], state="visible", timeout=15000)
                status_label.config(text=f"Status: Explore page loaded")
                root.update()
                time.sleep(0.5)

                # Click Search Input first, then type keyword
                if check_stop():
                    finish_playback()
                    return
                status_label.config(text=f"Status: Clicking Search...")
                root.update()
                page.click(selectors["search_input"])
                time.sleep(0.5)
                page.fill(selectors["search_input"], "")
                page.type(selectors["search_input"], keyword, delay=delays["type"])
                status_label.config(text=f"Status: Typed keyword '{keyword}'")
                root.update()

                # Press Enter
                if check_stop():
                    finish_playback()
                    return
                page.press(selectors["search_input"], "Enter")
                status_label.config(text=f"Status: Waiting for results...")
                root.update()
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                time.sleep(1)

                # Loop through profiles 1-5
                for i in range(1, 6):
                    if check_stop():
                        break
                    profile_key = f"profile_{i}"
                    selector = selectors.get(profile_key)
                    if not selector:
                        continue
                    
                    status_label.config(text=f"Status: Clicking Profile {i}")
                    root.update()
                    time.sleep(delays["profile_wait"] / 1000)
                    
                    if check_stop():
                        break
                    
                    try:
                        page.click(selector)
                        status_label.config(text=f"Status: Clicked Profile {i}")
                        root.update()
                        time.sleep(2)
                        
                        # Go back to search results
                        page.go_back()
                        status_label.config(text=f"Status: Back to results")
                        root.update()
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                        time.sleep(1)
                        
                        # Re-search for keyword before next profile (except last)
                        if i < 5:
                            status_label.config(text=f"Status: Re-searching for '{keyword}'")
                            root.update()
                            page.click(selectors["search_input"])
                            time.sleep(0.5)
                            page.fill(selectors["search_input"], "")
                            page.type(selectors["search_input"], keyword, delay=delays["type"])
                            page.press(selectors["search_input"], "Enter")
                            status_label.config(text=f"Status: Waiting for results...")
                            root.update()
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                            time.sleep(1)
                        
                    except Exception as e:
                        status_label.config(text=f"Status: Profile {i} failed - {e}")
                        root.update()
                        time.sleep(1)

                finish_playback()

            except Exception as e:
                status_label.config(text=f"Status: Error - {e}")
                root.update()
                finish_playback()

    play_running["thread"] = threading.Thread(target=run_automation, daemon=True)
    play_running["thread"].start()

def finish_playback():
    global play_running
    # Gracefully close browser via CDP (clean shutdown)
    if play_running.get("playwright_browser"):
        try:
            play_running["playwright_browser"].close()
        except:
            pass
        play_running["playwright_browser"] = None
    
    # Then terminate subprocess
    if play_running.get("browser_process"):
        try:
            play_running["browser_process"].terminate()
            play_running["browser_process"].wait(timeout=5)
        except:
            try:
                play_running["browser_process"].kill()
            except:
                pass
        play_running["browser_process"] = None

    play_running["active"] = False
    play_running["stop_flag"] = False
    root.after(0, lambda: (play_btn.config(text="▶", bg="#27AE60"), status_label.config(text="Status: Completed")))

root = tk.Tk()
root.title("ARKVUE - Instagram Automation")
root.geometry("500x400")
root.resizable(False, False)
root.configure(bg="#1E1E2E")

# Header
header = tk.Frame(root, bg="#1E1E2E")
header.pack(fill="x", pady=(20, 10))

tk.Label(header, text="ARKVUE", font=("Segoe UI", 24, "bold"), bg="#1E1E2E", fg="#00D9FF").pack()
tk.Label(header, text="Instagram Automation Tool", font=("Segoe UI", 10), bg="#1E1E2E", fg="#888").pack()

# Search Entry
search_frame = tk.Frame(root, bg="#1E1E2E")
search_frame.pack(pady=10, padx=30, fill="x")

search_entry = tk.Entry(search_frame, font=("Segoe UI", 12), relief="flat", bg="#2D2D44", fg="#FFF", insertbackground="#00D9FF")
search_entry.pack(fill="x", ipady=8)
search_entry.insert(0, "Enter keywords...")
search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, "end") if search_entry.get() == "Enter keywords..." else None)
search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "Enter keywords...") if not search_entry.get() else None)

# Play Button
play_btn = tk.Button(root, text="▶", font=("Segoe UI", 18, "bold"), bg="#27AE60", fg="white", relief="flat", cursor="hand2", width=4, height=1, command=play_script)
play_btn.pack(pady=15)

# Status
status_frame = tk.Frame(root, bg="#1E1E2E")
status_frame.pack(fill="x", padx=30, pady=5)

status_label = tk.Label(status_frame, text="Status: Ready", font=("Segoe UI", 9), bg="#1E1E2E", fg="#888", anchor="w")
status_label.pack(side="left")

mouse_label = tk.Label(status_frame, text="Mouse: (0, 0)", font=("Segoe UI", 9), bg="#1E1E2E", fg="#666", anchor="e")
mouse_label.pack(side="right")

# Nav Bar
nav_frame = tk.Frame(root, bg="#25253A")
nav_frame.pack(side="bottom", fill="x", pady=(10, 0))

tk.Button(nav_frame, text="⚙ Config", font=("Segoe UI", 9), bg="#3498DB", fg="white", relief="flat", cursor="hand2", padx=15, pady=5, command=show_config).pack(side="left", padx=20, pady=10)
tk.Button(nav_frame, text="📝 Prompt", font=("Segoe UI", 9), bg="#8E44AD", fg="white", relief="flat", cursor="hand2", padx=15, pady=5, command=show_system_prompt).pack(side="right", padx=20, pady=10)

update_mouse_coords()
root.mainloop()