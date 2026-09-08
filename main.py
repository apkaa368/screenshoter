import os
import time
from datetime import datetime
from pynput import keyboard, mouse
from PIL import Image, ImageGrab
import pywinctl
import sys
import subprocess

# ================= CONFIG =================
FINAL_WIDTH = 1200
FINAL_HEIGHT = 1000

LOGICAL_CROP_TOP = 40

WINDOW_LOGICAL_WIDTH = FINAL_WIDTH
WINDOW_LOGICAL_HEIGHT = FINAL_HEIGHT + LOGICAL_CROP_TOP

HOTKEY = '<ctrl>+<cmd>+x' 
HOTKEY_DISPLAY = 'Ctrl + Win + X' if os.name == 'nt' else 'Control + Command + X'
# ==========================================

from pathlib import Path

# Ustalenie systemowego folderu domowego i wybranie podfolderu Dokumenty/screenshots
home_dir = Path.home()
screenshots_dir = os.path.join(home_dir, "Documents", "screenshots")
waiting_for_click = False

def get_frontmost_app_and_resize(t_click):
    try:
        if sys.platform == "darwin":
            # macOS: Błyskawiczny dostęp przez natywny AppleScript (pomija narzut PyWinCtl)
            script = f"""
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                if frontApp is "Google Chrome" or frontApp is "Safari" or frontApp is "Brave Browser" or frontApp is "Microsoft Edge" or frontApp is "Firefox" then
                    tell application process frontApp
                        set standardWindows to (every window whose subrole is "AXStandardWindow")
                        if (count of standardWindows) = 0 then return "NOT_BROWSER"
                        set frontWindow to item 1 of standardWindows
                        set size of frontWindow to {{{WINDOW_LOGICAL_WIDTH}, {WINDOW_LOGICAL_HEIGHT}}}
                        set pos to position of frontWindow
                        return frontApp & "," & (item 1 of pos) & "," & (item 2 of pos) & "," & {WINDOW_LOGICAL_WIDTH} & "," & {WINDOW_LOGICAL_HEIGHT}
                    end tell
                else
                    return "NOT_BROWSER"
                end if
            end tell
            """
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            out = result.stdout.strip()
            if out == "NOT_BROWSER" or not out:
                return None
            parts = out.split(",")
            print(f"[⏱️ +{time.time()-t_click:.2f}s] Zakończono błyskawiczne skalowanie (macOS).")
            time.sleep(0.15)
            return {
                'app': parts[0],
                'x': int(parts[1]),
                'y': int(parts[2]),
                'w': int(parts[3]),
                'h': int(parts[4])
            }
        else:
            # Windows / Linux: Natywnie pywinctl działa na nich bardzo szybko
            win = pywinctl.getActiveWindow()
            if not win:
                return None
            
            app_name = getattr(win, 'app', win.title).lower()
            supported_browsers = ['chrome', 'safari', 'brave', 'edge', 'firefox']
            
            is_browser = any(b in app_name for b in supported_browsers)
            if not is_browser:
                return None
                
            print(f"[⏱️ +{time.time()-t_click:.2f}s] Wykryto okno (Windows/Linux). Zaczynam skalowanie...")
            win.resizeTo(WINDOW_LOGICAL_WIDTH, WINDOW_LOGICAL_HEIGHT)
            time.sleep(0.15) 
            
            box = win.box
            print(f"[⏱️ +{time.time()-t_click:.2f}s] Zakończono skalowanie.")
            return {
                'app': getattr(win, 'app', win.title),
                'x': int(box.left),
                'y': int(box.top),
                'w': int(box.width),
                'h': int(box.height)
            }
    except Exception as e:
        print(f"Error resizing window: {e}")
    return None

def take_screenshot(bounds, t_click):
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    final_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
    
    x, y, w, h = bounds['x'], bounds['y'], bounds['w'], bounds['h']
    
    print(f"[⏱️ +{time.time()-t_click:.2f}s] Capturing: {bounds['app']}")
    bbox = (x, y, x + w, y + h)
    
    try:
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        print(f"[⏱️ +{time.time()-t_click:.2f}s] Zrobiono surowy zrzut.")
        
        actual_width, actual_height = img.size
        
        scale_factor = actual_width / w if w > 0 else 1
        actual_crop = int(LOGICAL_CROP_TOP * scale_factor)
        
        cropped_img = img.crop((0, actual_crop, actual_width, actual_height))
        final_img = cropped_img.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.Resampling.LANCZOS)
        
        final_img.save(final_path)
        print(f"[⏱️ +{time.time()-t_click:.2f}s] Zapisano plik na dysku: {final_path}")
        play_success_sound()
        
    except Exception as e:
        print(f"Error taking screenshot: {e}")

def play_sound():
    if os.name == 'nt':
        try:
            import winsound
            winsound.MessageBeep()
        except:
            pass
    else:
        os.system("afplay /System/Library/Sounds/Ping.aiff &")

def play_success_sound():
    if os.name == 'nt':
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass
    else:
        os.system("afplay /System/Library/Sounds/Glass.aiff &")

def on_click(click_x, click_y, button, pressed):
    global waiting_for_click
    if waiting_for_click and pressed:
        t_click = time.time()
        waiting_for_click = False
        time.sleep(0.05)
        
        bounds = get_frontmost_app_and_resize(t_click)
        if bounds:
            take_screenshot(bounds, t_click)
        else:
            print("Unsupported application clicked.")

def on_activate_h():
    global waiting_for_click
    play_sound()
    print("Hotkey activated. Click a browser window...")
    waiting_for_click = True

if __name__ == "__main__":
    print(f"Screenshoter started.")
    print(f"Press '{HOTKEY_DISPLAY}', then click a browser window.")
    print(f"Press Ctrl+C to exit.")

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    with keyboard.GlobalHotKeys({HOTKEY: on_activate_h}) as h:
        h.join()
