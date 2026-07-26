import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import json
import os
import pyautogui
from pynput import mouse
import threading

CONFIG_FILE = "arkvue_config.json"

play_running = {"active": False, "thread": None, "stop_flag": False}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"system_prompt": "You are an AI assistant designed to help with automation tasks...\n\nBe precise, efficient, and safe in all operations.", "script_path": "", "delay_ms": 100, "retries": 3, "explore_coords": None, "search_coords": None, "profiles": {f"Profile {i}": None for i in range(1, 6)}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

config = load_config()

capture_mode = {"active": False, "target": None, "button": None, "label": None, "listener": None}

live_coords = {"x": 0, "y": 0}

def update_mouse_coords():
    x, y = pyautogui.position()
    live_coords["x"] = x
    live_coords["y"] = y
    mouse_label.config(text=f"Mouse: ({x}, {y})")
    root.after(50, update_mouse_coords)

def start_capture(target, button, label):
    capture_mode["active"] = True
    capture_mode["target"] = target
    capture_mode["button"] = button
    capture_mode["label"] = label
    button.config(text="Click anywhere...", bg="#E74C3C")
    
    def on_click(x, y, btn, pressed):
        if not capture_mode["active"]:
            return False
        if pressed and btn == mouse.Button.left:
            root.after(0, lambda: finish_capture(live_coords["x"], live_coords["y"]))
            return False
        return True
    
    def finish_capture(x, y):
        capture_mode["button"].config(text=f"({x}, {y})", bg="#27AE60")
        capture_mode["label"].config(text=f"Coords: ({x}, {y})")
        target = capture_mode["target"]
        if target == "explore":
            config["explore_coords"] = {"x": x, "y": y}
        elif target == "search":
            config["search_coords"] = {"x": x, "y": y}
        elif target.startswith("Profile"):
            config.setdefault("profiles", {})[target] = {"x": x, "y": y}
        save_config(config)
        capture_mode["active"] = False
        capture_mode["listener"].stop()
        capture_mode["listener"] = None
    
    listener = mouse.Listener(on_click=on_click)
    capture_mode["listener"] = listener
    listener.start()

def cancel_capture():
    if capture_mode["active"]:
        capture_mode["button"].config(text=capture_mode["button"].original_text, bg=capture_mode["button"].original_bg)
        capture_mode["active"] = False
    if capture_mode["listener"]:
        capture_mode["listener"].stop()
        capture_mode["listener"] = None

def show_config():
    config_win = tk.Toplevel(root)
    config_win.title("Configuration")
    config_win.geometry("450x600")
    config_win.resizable(False, False)
    config_win.transient(root)
    config_win.grab_set()
    config_win.configure(bg="#ECF0F1")
    
    # Scrollable frame
    canvas = tk.Canvas(config_win, bg="#ECF0F1", highlightthickness=0)
    scrollbar = tk.Scrollbar(config_win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#ECF0F1")
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    
    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _unbind_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")
    
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", _unbind_mousewheel)
    
    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")
    
    tk.Label(scrollable_frame, text="Configuration", font=("Segoe UI", 14, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=15)
    
    # Global Coordinates (at top)
    tk.Label(scrollable_frame, text="Global Coordinates (fallback)", font=("Segoe UI", 11, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=5)
    
    global_frame = tk.Frame(scrollable_frame, bg="#ECF0F1")
    global_frame.pack(pady=5)
    
    btn_style2 = {"font": ("Segoe UI", 10, "bold"), "width": 22, "height": 1, "relief": "flat", "cursor": "hand2"}
    
    explore_btn = tk.Button(global_frame, text="🔍  Explore Page", bg="#3498DB", fg="white", **btn_style2)
    explore_btn.original_text = "🔍  Explore Page"
    explore_btn.original_bg = "#3498DB"
    explore_btn.pack(pady=4)
    
    explore_coords_label = tk.Label(scrollable_frame, text=f"Coords: {config.get('explore_coords', 'Not set')}", font=("Segoe UI", 9), bg="#ECF0F1", fg="#2C3E50")
    explore_coords_label.pack(pady=1)
    
    def start_explore_capture():
        start_capture("explore", explore_btn, explore_coords_label)
    
    explore_btn.config(command=start_explore_capture)
    
    search_btn = tk.Button(global_frame, text="🔎  Search Bar", bg="#27AE60", fg="white", **btn_style2)
    search_btn.original_text = "🔎  Search Bar"
    search_btn.original_bg = "#27AE60"
    search_btn.pack(pady=4)
    
    search_coords_label = tk.Label(scrollable_frame, text=f"Coords: {config.get('search_coords', 'Not set')}", font=("Segoe UI", 9), bg="#ECF0F1", fg="#2C3E50")
    search_coords_label.pack(pady=1)
    
    def start_search_capture():
        start_capture("search", search_btn, search_coords_label)
    
    search_btn.config(command=start_search_capture)
    
    # Divider
    tk.Frame(scrollable_frame, height=2, bg="#BDC3C7").pack(fill="x", padx=20, pady=10)
    
    # Profile buttons (below global) - single buttons like explore/search
    tk.Label(scrollable_frame, text="Profiles (1-5)", font=("Segoe UI", 11, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=5)
    
    btn_frame = tk.Frame(scrollable_frame, bg="#ECF0F1")
    btn_frame.pack(pady=5)
    
    btn_style = {"font": ("Segoe UI", 11, "bold"), "width": 25, "height": 2, "relief": "flat", "cursor": "hand2"}
    
    for i in range(1, 6):
        profile_name = f"Profile {i}"
        profile_coord = config.get("profiles", {}).get(profile_name)
        coord_text = f"({profile_coord['x']}, {profile_coord['y']})" if profile_coord else "Not set"
        
        btn = tk.Button(btn_frame, text=f"{profile_name}", bg="#8E44AD", fg="white", **btn_style)
        btn.original_text = f"{profile_name}"
        btn.original_bg = "#8E44AD"
        btn.pack(pady=4)
        
        label = tk.Label(scrollable_frame, text=f"Coords: {coord_text}", font=("Segoe UI", 9), bg="#ECF0F1", fg="#2C3E50")
        label.pack(pady=1)
        
        btn.config(command=lambda b=btn, l=label, n=profile_name: start_capture(n, b, l))
    
    tk.Button(scrollable_frame, text="Close", font=("Segoe UI", 9), bg="#E74C3C", fg="white", relief="flat", cursor="hand2", padx=20, pady=3, command=config_win.destroy).pack(pady=15)

def play_script():
    global play_running
    
    # If already running, stop it
    if play_running["active"]:
        play_running["stop_flag"] = True
        play_btn.config(text="▶", bg="#27AE60")
        play_running["active"] = False
        status_label.config(text="Status: Stopped by user")
        return
    
    explore = config.get("explore_coords")
    search = config.get("search_coords")
    keyword = search_entry.get().strip()
    
    if not keyword or keyword == "Enter keywords...":
        messagebox.showwarning("Empty Keyword", "Keyword box is empty. Please enter a keyword.")
        status_label.config(text="Status: Keyword box is empty")
        return
    
    if not explore or not search:
        missing = []
        if not explore:
            missing.append("Explore Page")
        if not search:
            missing.append("Search Bar")
        messagebox.showwarning("Missing Coordinates", f"Please set coordinates for: {', '.join(missing)}")
        status_label.config(text=f"Status: Missing coordinates for {', '.join(missing)}")
        return
    
    play_running["active"] = True
    play_running["stop_flag"] = False
    play_btn.config(text="■", bg="#E74C3C")
    status_label.config(text="Status: Running...")
    
    def run_automation():
        import time
        
        def run_cycle():
            if play_running["stop_flag"]:
                return False
            # Click explore page
            pyautogui.click(explore["x"], explore["y"])
            status_label.config(text=f"Status: Clicked Explore at ({explore['x']}, {explore['y']})")
            root.update()
            time.sleep(0.5)
            
            if play_running["stop_flag"]:
                return False
            # Click search bar 2 times with minor delay
            pyautogui.click(search["x"], search["y"])
            time.sleep(0.2)
            pyautogui.click(search["x"], search["y"])
            status_label.config(text=f"Status: Clicked Search 2x at ({search['x']}, {search['y']})")
            root.update()
            time.sleep(0.3)
            
            if play_running["stop_flag"]:
                return False
            # Press backspace
            pyautogui.press('backspace')
            time.sleep(0.1)
            
            # Type keyword
            pyautogui.write(keyword)
            status_label.config(text=f"Status: Typed keyword '{keyword}'")
            root.update()
            
            # Wait 2 seconds after each search
            time.sleep(2)
            return True
        
        # First cycle (global)
        if not run_cycle():
            finish_playback()
            return
        
        # Then loop through profiles 1-5
        for i in range(1, 6):
            if play_running["stop_flag"]:
                break
            profile_name = f"Profile {i}"
            profile_coord = config.get("profiles", {}).get(profile_name)
            
            if profile_coord:
                if play_running["stop_flag"]:
                    break
                # Wait 2 seconds before clicking profile
                time.sleep(1)
                
                if play_running["stop_flag"]:
                    break
                # Click profile
                pyautogui.click(profile_coord["x"], profile_coord["y"])
                status_label.config(text=f"Status: Clicked {profile_name} at ({profile_coord['x']}, {profile_coord['y']})")
                root.update()
                time.sleep(2)
                
                if play_running["stop_flag"]:
                    break
                # Run cycle again
                if not run_cycle():
                    break
            else:
                status_label.config(text=f"Status: {profile_name} not configured, skipping")
                root.update()
                time.sleep(0.5)
        
        finish_playback()
    
    def finish_playback():
        play_running["active"] = False
        play_running["stop_flag"] = False
        root.after(0, lambda: (play_btn.config(text="▶", bg="#27AE60"), status_label.config(text="Status: Completed")))
    
    play_running["thread"] = threading.Thread(target=run_automation, daemon=True)
    play_running["thread"].start()

def show_system_prompt():
    prompt_win = tk.Toplevel(root)
    prompt_win.title("System Prompt")
    prompt_win.geometry("500x400")
    prompt_win.resizable(False, False)
    prompt_win.transient(root)
    prompt_win.grab_set()
    prompt_win.configure(bg="#2C3E50")
    
    header = tk.Frame(prompt_win, bg="#34495E", height=60)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(header, text="SYSTEM PROMPT", font=("Segoe UI", 13, "bold"), bg="#34495E", fg="#ECF0F1").pack(expand=True)
    
    tk.Label(prompt_win, text="Enter your system prompt:", font=("Segoe UI", 10), bg="#2C3E50", fg="#ECF0F1").pack(pady=(15, 5))
    
    text_area = scrolledtext.ScrolledText(prompt_win, width=55, height=15, font=("Consolas", 10), bg="#ECF0F1", fg="#2C3E50", relief="flat", borderwidth=0)
    text_area.pack(padx=20, pady=10, fill="both", expand=True)
    text_area.insert("1.0", config.get("system_prompt", ""))
    
    def save_prompt():
        config["system_prompt"] = text_area.get("1.0", "end-1c")
        save_config(config)
        messagebox.showinfo("Saved", "System prompt saved!")
        status_label.config(text="Status: System prompt saved  |  ARKVUE v1.0")
        prompt_win.destroy()
    
    btn_frame = tk.Frame(prompt_win, bg="#2C3E50")
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="Save", width=14, bg="#27AE60", fg="white", font=("Segoe UI", 10, "bold"), command=save_prompt).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Cancel", width=14, bg="#E74C3C", fg="white", font=("Segoe UI", 10, "bold"), command=prompt_win.destroy).pack(side="left", padx=10)

def save_main_prompt():
    config["system_prompt"] = prompt_text.get("1.0", "end-1c")
    save_config(config)
    messagebox.showinfo("Saved", "System prompt saved to config!")
    status_label.config(text="Status: System prompt saved  |  ARKVUE v1.0")

def search_keywords():
    query = search_entry.get()
    if query:
        messagebox.showinfo("Search", f"Searching for: {query}\n\n[Simulated search results would appear here]")
        status_label.config(text=f"Status: Searched for '{query}'  |  ARKVUE v1.0")
    else:
        messagebox.showwarning("Empty", "Enter a keyword to search")

root = tk.Tk()
root.title("ARKVUE Automation")
root.geometry("900x550")
root.minsize(800, 500)
root.configure(bg="#ECF0F1")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10), padding=8)

top_bar = tk.Frame(root, bg="#2C3E50", height=60)
top_bar.pack(fill="x")
top_bar.pack_propagate(False)

logo_label = tk.Label(top_bar, text="ARKVUE", font=("Segoe UI", 18, "bold"), fg="#ECF0F1", bg="#2C3E50")
logo_label.pack(side="left", padx=30, pady=15)

play_btn = tk.Button(top_bar, text="▶", font=("Segoe UI", 18, "bold"), bg="#27AE60", fg="white", relief="flat", cursor="hand2", width=3, height=1, command=play_script)
play_btn.pack(side="right", padx=30, pady=10)

prompt_btn = tk.Button(top_bar, text="📝 System Prompt", font=("Segoe UI", 10, "bold"), bg="#9B59B6", fg="white", relief="flat", cursor="hand2", padx=15, pady=5, command=show_system_prompt)
prompt_btn.pack(side="right", padx=15, pady=10)

config_btn = tk.Button(top_bar, text="⚙  Configuration", font=("Segoe UI", 10, "bold"), bg="#3498DB", fg="white", relief="flat", cursor="hand2", padx=20, pady=5, command=show_config)
config_btn.pack(side="left", padx=15, pady=10)

main_frame = tk.Frame(root, bg="#ECF0F1")
main_frame.pack(expand=True, fill="both", padx=40, pady=20)

card = tk.Frame(main_frame, bg="white", relief="flat", borderwidth=1)
card.pack(expand=True, fill="both", padx=20, pady=20)

tk.Label(card, text="Automation Control Panel", font=("Segoe UI", 18, "bold"), bg="white", fg="#2C3E50").pack(pady=(20, 10))
tk.Label(card, text="Manage and execute your automation scripts", font=("Segoe UI", 10), bg="white", fg="#7F8C8D").pack(pady=(0, 20))

search_frame = tk.Frame(card, bg="white")
search_frame.pack(fill="x", padx=30, pady=(0, 15))
tk.Label(search_frame, text="🔍 Keywords:", font=("Segoe UI", 10), bg="white", fg="#2C3E50").pack(side="left", padx=(0, 10))
search_entry = tk.Entry(search_frame, font=("Segoe UI", 10), width=40, relief="flat", bg="#F8F9FA", fg="#2C3E50")
search_entry.pack(side="left", ipady=4)
search_entry.insert(0, "Enter keywords...")
search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, "end") if search_entry.get() == "Enter keywords..." else None)

status_bar = tk.Frame(root, bg="#BDC3C7", height=30)
status_bar.pack(fill="x", side="bottom")
status_bar.pack_propagate(False)

status_label = tk.Label(status_bar, text="Ready  |  ARKVUE v1.0", font=("Segoe UI", 9), bg="#BDC3C7", fg="#2C3E50")
status_label.pack(side="left", padx=20)

mouse_label = tk.Label(status_bar, text="Mouse: (0, 0)", font=("Segoe UI", 9), bg="#BDC3C7", fg="#2C3E50")
mouse_label.pack(side="left", padx=20)

click_label = tk.Label(status_bar, text="Click: (0, 0)", font=("Segoe UI", 9), bg="#BDC3C7", fg="#E74C3C")
click_label.pack(side="left", padx=20)

tk.Label(status_bar, text="© 2024 ARKVUE Automation", font=("Segoe UI", 9), bg="#BDC3C7", fg="#7F8C8D").pack(side="right", padx=20)

update_mouse_coords()
root.mainloop()