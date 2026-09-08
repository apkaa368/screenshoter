import os
import time
from datetime import datetime
from pynput import keyboard, mouse
from PIL import Image, ImageGrab
import pywinctl

# ================= CONFIG =================
FINAL_WIDTH = 1200
FINAL_HEIGHT = 1000

LOGICAL_CROP_TOP = 42 

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

def get_frontmost_app_and_resize():
    try:
        win = pywinctl.getActiveWindow()
        if not win:
            return None
        
        app_name = getattr(win, 'app', win.title).lower()
        supported_browsers = ['chrome', 'safari', 'brave', 'edge', 'firefox']
        
        is_browser = any(b in app_name for b in supported_browsers)
        if not is_browser:
            return None
            
        win.moveTo(100, 100)
        win.resizeTo(WINDOW_LOGICAL_WIDTH, WINDOW_LOGICAL_HEIGHT)
        time.sleep(0.5) 
        
        box = win.box
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

def take_screenshot(bounds):
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    final_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
    
    x, y, w, h = bounds['x'], bounds['y'], bounds['w'], bounds['h']
    
    print(f"Capturing: {bounds['app']}")
    bbox = (x, y, x + w, y + h)
    
    try:
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        actual_width, actual_height = img.size
        
        scale_factor = actual_width / w if w > 0 else 1
        actual_crop = int(LOGICAL_CROP_TOP * scale_factor)
        
        cropped_img = img.crop((0, actual_crop, actual_width, actual_height))
        final_img = cropped_img.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.Resampling.LANCZOS)
        
        final_img.save(final_path)
        print(f"Saved: {final_path}")
        
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

def on_click(click_x, click_y, button, pressed):
    global waiting_for_click
    if waiting_for_click and pressed:
        waiting_for_click = False
        time.sleep(0.3)
        
        bounds = get_frontmost_app_and_resize()
        if bounds:
            take_screenshot(bounds)
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
