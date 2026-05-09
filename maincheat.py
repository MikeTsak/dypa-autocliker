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

# --- HIDE PYTORCH WARNINGS ---
warnings.filterwarnings("ignore", category=UserWarning)


# ==========================================
# BOOTING / SPLASH SCREEN
# ==========================================
def show_splash():
    splash_layout = [
        [sg.Text("DYPA Ultimate Bot", font=("Arial", 25, "bold"), text_color="darkblue")],
        [sg.Text("Created by MikeTsak.gr", font=("Arial", 12, "italic"))],
        [sg.Text("Initializing OCR Engine...", key="-STATUS-", font=("Arial", 10))],
        [sg.ProgressBar(100, orientation='h', size=(20, 20), key='-PROG-')]
    ]
    splash_window = sg.Window("Loading...", splash_layout, no_titlebar=True, keep_on_top=True, finalize=True,
                              element_justification='c')

    # Simulate loading progress while initializing OCR
    for i in range(1, 50):
        splash_window['-PROG-'].update(i)
        splash_window.read(timeout=10)

    # Initialize OCR
    ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)

    for i in range(50, 101):
        splash_window['-PROG-'].update(i)
        splash_window.read(timeout=10)

    splash_window.close()
    return ocr_reader


# Trigger splash and load engine
reader = show_splash()

# ==========================================
# SETTINGS & CONFIGURATION
# ==========================================
SPEEDS = {
    'TURBO': (15, 25),  # 15-25 seconds
    'FAST': (60, 240),  # 1-4 mins
    'NORMAL': (240, 420),  # 4-7 mins
    'SLOW': (360, 540)  # 6-9 mins
}

TARGET_COORDINATES = (1738, 864)
SESSION_START_SECONDS = 80 * 60  # 1 hour 20 minutes

# Humanizer intervals
MOVE_COOLDOWN_NORMAL = (15, 45)
MOVE_COOLDOWN_TURBO = (5, 7)


# ==========================================
# SOUND & LOGIC FUNCTIONS
# ==========================================
def play_click_sound(muted):
    if not muted:
        winsound.Beep(800, 60)


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

    def get_eta_str(low, high):
        total_sec = remaining * ((low + high) // 2)
        return f"{total_sec // 3600}h {(total_sec % 3600) // 60}m"

    return f"T:{get_eta_str(*SPEEDS['TURBO'])} | F:{get_eta_str(*SPEEDS['FAST'])} | N:{get_eta_str(*SPEEDS['NORMAL'])} | S:{get_eta_str(*SPEEDS['SLOW'])}"


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
    except:
        return None, "Vision Error"


def read_progress_data(bx, by):
    try:
        box = (max(0, bx - 1000), max(0, by - 40), max(0, bx - 150), by + 40)
        img = ImageGrab.grab(bbox=box)
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
        nums = re.findall(r'\d+', " ".join(reader.readtext(thresh, detail=0)))
        if len(nums) >= 2: return int(nums[0]), int(nums[-1])
    except:
        pass
    return None, None


# ==========================================
# MAIN UI SETUP
# ==========================================
sg.theme('SystemDefault')

layout = [
    [sg.Text("Grand Session Timer:", font=("Arial", 10)),
     sg.Text("01:20:00", key="-GRAND-", font=("Arial", 14, "bold"), text_color="darkblue")],
    [sg.HSeparator()],
    [sg.Radio('Turbo', 'SPEED', key='-TURBO-', text_color="red"),
     sg.Radio('Fast', 'SPEED', key='-FAST-'),
     sg.Radio('Normal', 'SPEED', default=True, key='-NORMAL-'),
     sg.Radio('Slow', 'SPEED', key='-SLOW-')],
    [sg.Checkbox('Mute Clicks', key='-MUTE-'), sg.Checkbox('Humanizer (Moves)', default=True, key='-MOVE_ACTIVE-')],
    [sg.HSeparator()],
    [sg.Text("Progress:"), sg.Text("? / ?", key="-PROGRESS-", font=("Arial", 11, "bold")),
     sg.Text("Next Click:"), sg.Text("00:00", key="-TIMER-", font=("Arial", 14, "bold"))],
    [sg.Text("Humanizer Timer:"), sg.Text("00:00", key="-MOVE_TIMER-", font=("Arial", 11, "bold"), text_color="green")],
    [sg.Text("Live ETAs:", font=("Arial", 9, "bold"))],
    [sg.Text("T: -- | F: -- | N: -- | S: --", key="-ETA-", font=("Arial", 9, "bold"), text_color="darkred")],
    [sg.Text("Log:"), sg.Text("System Ready", key="-LOG-", size=(40, 1), font=("Arial", 8))],
    [sg.HSeparator()],
    [sg.Button("Start Bot", button_color="green", size=(10, 1)), sg.Button("Stop Bot", size=(10, 1)),
     sg.Button("Sound Test", size=(10, 1))],
    [sg.Button("Test Vision", size=(10, 1), button_color="blue"), sg.Button("Exit", button_color="red", size=(10, 1))]
]

window = sg.Window("DYPA Ultimate Bot V7.0 - MikeTsak.gr", layout, keep_on_top=True, element_justification='c',
                   size=(500, 480))

# State variables
bot_active = False
grand_timer = SESSION_START_SECONDS
next_click_timer = 0
next_move_timer = 0
last_update = time.time()

# ==========================================
# MAIN EVENT LOOP
# ==========================================
while True:
    event, values = window.read(timeout=100)

    if keyboard.is_pressed('esc') or event in (sg.WIN_CLOSED, "Exit"): break

    if event == "Sound Test":
        play_click_sound(False);
        time.sleep(0.5);
        play_alarm()

    if event == "Start Bot":
        bot_active = True
        grand_timer = SESSION_START_SECONDS
        next_click_timer = get_random_delay(values)
        move_range = MOVE_COOLDOWN_TURBO if values['-TURBO-'] else MOVE_COOLDOWN_NORMAL
        next_move_timer = random.randint(*move_range)
        last_update = time.time()
        window["-LOG-"].update("Bot Running...")

    if event == "Stop Bot":
        bot_active = False
        window["-GRAND-"].update(format_time(SESSION_START_SECONDS))
        window["-LOG-"].update("Bot Stopped Manual")

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
            grand_timer -= 1;
            next_click_timer -= 1;
            next_move_timer -= 1

            window["-GRAND-"].update(format_time(grand_timer))
            window["-TIMER-"].update(format_time(next_click_timer))
            window["-MOVE_TIMER-"].update(format_time(next_move_timer))

            if grand_timer <= 0:
                bot_active = False
                window["-LOG-"].update("SESSION TIME EXPIRED")
                play_alarm()

            # --- UPDATED PRIORITY LOGIC ---
            # 1. Check Clicker first. If it's time to click, we ignore Humanizer for this second.
            if next_click_timer <= 0:
                loc, msg = find_button_by_color()
                if loc:
                    cur, tot = read_progress_data(loc[0], loc[1])
                    if cur and tot:
                        window["-PROGRESS-"].update(f"{cur} / {tot}")
                        window["-ETA-"].update(calculate_all_etas(cur, tot))
                        if (tot - cur) <= 5:
                            bot_active = False
                            window["-LOG-"].update("ALARM: 5 SLIDES REMAINING")
                            play_alarm()
                            continue

                    play_click_sound(values['-MUTE-'])
                    click_dur = 0.3 if values['-TURBO-'] else 0.7
                    pyautogui.moveTo(loc, duration=click_dur)
                    pyautogui.click()

                    # Reset Click Timer
                    next_click_timer = get_random_delay(values)
                    # Reset Humanizer Timer - Push it back so it doesn't move immediately after click
                    next_move_timer = random.randint(5, 10)
                    window["-LOG-"].update("Clicked Next - Waiting...")
                else:
                    window["-LOG-"].update("Button lost - retrying...")
                    next_click_timer = 3 if values['-TURBO-'] else 5

            # 2. Only check Humanizer if we AREN'T clicking
            elif values['-MOVE_ACTIVE-'] and next_move_timer <= 0:
                w, h = pyautogui.size()
                move_dur = 0.6 if values['-TURBO-'] else 1.5
                pyautogui.moveTo(random.randint(100, w - 100), random.randint(100, h - 100), duration=move_dur)

                # Reset Humanizer timer
                m_range = MOVE_COOLDOWN_TURBO if values['-TURBO-'] else MOVE_COOLDOWN_NORMAL
                next_move_timer = random.randint(*m_range)

window.close()