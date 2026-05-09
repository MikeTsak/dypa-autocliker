import FreeSimpleGUI as sg
import pyautogui
import time
import random
import keyboard
import cv2
import numpy as np
from PIL import ImageGrab
import easyocr
import re
import warnings
import winsound
import os
import sys

# --- HIDE PYTORCH WARNINGS ---
warnings.filterwarnings("ignore", category=UserWarning)

# ==========================================
# EXE PATH RESOLUTION (CRITICAL FOR PACKAGING)
# ==========================================
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ==========================================
# BOOTING / SPLASH SCREEN
# ==========================================
def show_splash():
    splash_layout = [
        [sg.Text("DYPA Ultimate Bot", font=("Segoe UI", 25, "bold"), text_color="#1c4e80")],
        [sg.Text("Created by MikeTsak.gr", font=("Segoe UI", 12, "italic"))],
        [sg.Text("Initializing OCR Engine...", key="-STATUS-", font=("Segoe UI", 10))],
        [sg.ProgressBar(100, orientation='h', size=(20, 20), key='-PROG-', bar_color=('#1c4e80', '#eeeeee'))]
    ]
    splash_window = sg.Window("Loading...", splash_layout, no_titlebar=True, keep_on_top=True, finalize=True,
                              element_justification='c', background_color='#ffffff')

    for i in range(1, 30):
        splash_window['-PROG-'].update(i)
        splash_window.read(timeout=1)

    # Point EasyOCR to the internal 'models' folder for EXE portability
    # Use 'models' (plural) to match the packaging instructions below
    models_path = get_resource_path('models')
    
    if not os.path.exists(models_path):
        os.makedirs(models_path, exist_ok=True)

    # reader must be global or returned to be used in vision functions
    ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False, model_storage_directory=models_path)

    for i in range(30, 101):
        splash_window['-PROG-'].update(i)
        splash_window.read(timeout=1)

    splash_window.close()
    return ocr_reader

# Global reader instance
reader = show_splash()

# ==========================================
# SETTINGS & CONFIGURATION
# ==========================================
SPEEDS = {
    'TURBO': (15, 25),
    'FAST': (60, 240),
    'NORMAL': (240, 420),
    'SLOW': (360, 540)
}

SESSION_START_SECONDS = 80 * 60
MOVE_COOLDOWN_NORMAL = (15, 45)
MOVE_COOLDOWN_TURBO = (5, 7)

# ==========================================
# SOUND & LOGIC FUNCTIONS
# ==========================================
def play_click_sound(muted):
    if not muted: winsound.Beep(800, 60)

def play_alarm():
    for _ in range(4):
        winsound.Beep(2500, 200)
        winsound.Beep(1800, 200)

def get_random_delay(values):
    if values['-TURBO-']: return random.randint(*SPEEDS['TURBO'])
    if values['-FAST-']: return random.randint(*SPEEDS['FAST'])
    if values['-NORMAL-']: return random.randint(*SPEEDS['NORMAL'])
    return random.randint(*SPEEDS['SLOW'])

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:01d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def calculate_all_etas(current, total):
    remaining = total - current
    if remaining <= 0: return "Done!"
    def get_eta(low, high):
        total_sec = remaining * ((low + high) // 2)
        return f"{total_sec // 3600}h {(total_sec % 3600) // 60}m"
    return f"T:{get_eta(*SPEEDS['TURBO'])} | F:{get_eta(*SPEEDS['FAST'])} | N:{get_eta(*SPEEDS['NORMAL'])} | S:{get_eta(*SPEEDS['SLOW'])}"

# ==========================================
# VISION FUNCTIONS
# ==========================================
def find_button_by_color():
    try:
        screen_bgr = cv2.cvtColor(np.array(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([95, 80, 100]), np.array([125, 255, 255]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_center, largest_area = None, 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if h > 0 and 1.5 < (w / h) < 5.0 and 500 < area < 30000:
                if area > largest_area:
                    largest_area, best_center = area, (x + (w // 2), y + (h // 2))
        return best_center, f"Vision: OK ({largest_area}px)" if best_center else "Vision: Searching..."
    except: return None, "Vision Error"

def read_progress_data(bx, by):
    try:
        box = (max(0, bx - 1000), max(0, by - 40), max(0, bx - 150), by + 40)
        img = ImageGrab.grab(bbox=box)
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
        results = reader.readtext(thresh, detail=0)
        nums = re.findall(r'\d+', " ".join(results))
        if len(nums) >= 2: return int(nums[0]), int(nums[-1])
    except: pass
    return None, None

# ==========================================
# MODERN UI SETUP
# ==========================================
sg.theme('LightGray1')

timer_frame = [
    [sg.Text("SESSION TIME", font=("Segoe UI", 9, "bold"), text_color="#555555")],
    [sg.Text("01:20:00", key="-GRAND-", font=("Segoe UI", 24, "bold"), text_color="#1c4e80")],
    [sg.Text("NEXT CLICK", font=("Segoe UI", 9, "bold"), text_color="#555555"),
     sg.Text("00:00", key="-TIMER-", font=("Segoe UI", 12, "bold"), text_color="#d9534f")]
]

progress_frame = [
    [sg.Text("PROGRESS", font=("Segoe UI", 9, "bold"), text_color="#555555")],
    [sg.Text("? / ?", key="-PROGRESS-", font=("Segoe UI", 18, "bold"), text_color="#333333")],
    [sg.Text("HUMANIZER", font=("Segoe UI", 9, "bold"), text_color="#555555"),
     sg.Text("00:00", key="-MOVE_TIMER-", font=("Segoe UI", 10, "bold"), text_color="#5cb85c")]
]

layout = [
    [sg.Text("DYPA ULTIMATE BOT", font=("Segoe UI", 18, "bold"), text_color="#1c4e80"), sg.Push(),
     sg.Button("Manual", button_color="#777777", size=(8, 1))],
    [sg.HSeparator()],
    [sg.Text("Select Speed Profile:", font=("Segoe UI", 10, "bold"))],
    [sg.Radio('Turbo', 'SPEED', key='-TURBO-', text_color="#d9534f"),
     sg.Radio('Fast', 'SPEED', key='-FAST-'),
     sg.Radio('Normal', 'SPEED', default=True, key='-NORMAL-'),
     sg.Radio('Slow', 'SPEED', key='-SLOW-')],
    [sg.Checkbox('Mute Clicks', key='-MUTE-'), sg.Checkbox('Humanizer Moves', default=True, key='-MOVE_ACTIVE-')],
    [sg.Frame("", timer_frame, element_justification='c', border_width=0, p=(10, 10)),
     sg.VerticalSeparator(),
     sg.Frame("", progress_frame, element_justification='c', border_width=0, p=(10, 10))],
    [sg.Text("ESTIMATED FINISH TIMES", font=("Segoe UI", 8, "bold"), text_color="#777777")],
    [sg.Text("T: -- | F: -- | N: -- | S: --", key="-ETA-", font=("Segoe UI", 9, "bold"), text_color="#1c4e80",
             background_color="#f9f9f9", expand_x=True, justification='c')],
    [sg.Text("LOG:", font=("Segoe UI", 8, "bold")),
     sg.Text("Ready to start", key="-LOG-", font=("Segoe UI", 8), text_color="#555555")],
    [sg.Button("START BOT", key="Start Bot", button_color="#5cb85c", size=(15, 2), font=("Segoe UI", 10, "bold")),
     sg.Button("STOP BOT", key="Stop Bot", button_color="#d9534f", size=(15, 2), font=("Segoe UI", 10, "bold"))],
    [sg.Button("Sound Test", size=(12, 1)), sg.Button("Test Vision", size=(12, 1)),
     sg.Button("Exit", button_color="#333333", size=(12, 1))],
    [sg.HSeparator(p=(0, 10))],
    [sg.Text("Made by MikeTsak.gr", font=("Segoe UI", 8, "italic"), text_color="#aaaaaa", justification='c',
             expand_x=True)]
]

window = sg.Window("DYPA Ultimate Bot V7.5", layout, keep_on_top=True, element_justification='c', size=(550, 600),
                   finalize=True)

bot_active, grand_timer, next_click_timer, next_move_timer, last_update = False, SESSION_START_SECONDS, 0, 0, time.time()

while True:
    event, values = window.read(timeout=100)
    if keyboard.is_pressed('esc') or event in (sg.WIN_CLOSED, "Exit"): break

    if event == "Manual":
        sg.popup(
            "DYPA BOT MANUAL\n\n1. Press 'Test Vision' to verify button detection.\n2. Choose a Speed Profile.\n3. Press 'START BOT'.\n4. Use 'ESC' for Emergency Stop.\n5. Bot stops automatically 5 slides before end.",
            title="Manual", keep_on_top=True)

    if event == "Sound Test":
        play_click_sound(False); time.sleep(0.5); play_alarm()

    if event == "Start Bot":
        bot_active, grand_timer, last_update = True, SESSION_START_SECONDS, time.time()
        next_click_timer = get_random_delay(values)
        next_move_timer = random.randint(*(MOVE_COOLDOWN_TURBO if values['-TURBO-'] else MOVE_COOLDOWN_NORMAL))
        window["-LOG-"].update("RUNNING...")

    if event == "Stop Bot":
        bot_active = False
        window["-LOG-"].update("STOPPED")

    if event == "Test Vision":
        loc, msg = find_button_by_color()
        if loc:
            pyautogui.moveTo(loc, duration=0.5)
            cur, tot = read_progress_data(loc[0], loc[1])
            if cur:
                window["-PROGRESS-"].update(f"{cur} / {tot}")
                window["-ETA-"].update(calculate_all_etas(cur, tot))
        window["-LOG-"].update(msg)

    if bot_active:
        now = time.time()
        if now - last_update >= 1:
            last_update = now
            grand_timer -= 1; next_click_timer -= 1; next_move_timer -= 1
            window["-GRAND-"].update(format_time(grand_timer))
            window["-TIMER-"].update(format_time(next_click_timer))
            window["-MOVE_TIMER-"].update(format_time(next_move_timer))

            if grand_timer <= 0:
                bot_active = False
                window["-LOG-"].update("TIME EXPIRED")
                play_alarm()

            if next_click_timer <= 0:
                loc, msg = find_button_by_color()
                if loc:
                    cur, tot = read_progress_data(loc[0], loc[1])
                    if cur and tot:
                        window["-PROGRESS-"].update(f"{cur} / {tot}")
                        window["-ETA-"].update(calculate_all_etas(cur, tot))
                        if (tot - cur) <= 5:
                            bot_active = False
                            window["-LOG-"].update("NEAR COMPLETION")
                            play_alarm()
                            continue
                    play_click_sound(values['-MUTE-'])
                    dur = 0.3 if values['-TURBO-'] else 0.7
                    pyautogui.moveTo(loc, duration=dur)
                    pyautogui.click()
                    next_click_timer = get_random_delay(values)
                    next_move_timer = random.randint(5, 10)
                else:
                    next_click_timer = 3 if values['-TURBO-'] else 5

            elif values['-MOVE_ACTIVE-'] and next_move_timer <= 0:
                w, h = pyautogui.size()
                pyautogui.moveTo(random.randint(100, w - 100), random.randint(100, h - 100),
                                 duration=0.6 if values['-TURBO-'] else 1.5)
                m_range = MOVE_COOLDOWN_TURBO if values['-TURBO-'] else MOVE_COOLDOWN_NORMAL
                next_move_timer = random.randint(*m_range)

window.close()