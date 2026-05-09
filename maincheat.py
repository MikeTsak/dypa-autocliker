import FreeSimpleGUI as sg
import pyautogui
import time
import random
import keyboard
import cv2
import numpy as np
from PIL import ImageGrab

# ==========================================
# SETTINGS & CONFIGURATION
# ==========================================
MIN_SECONDS = 330
MAX_SECONDS = 550
TARGET_COORDINATES = (1738, 864)


def get_random_delay():
    return random.randint(MIN_SECONDS, MAX_SECONDS)


def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


# --- THE TEMPLATE-FREE BLOB DETECTOR ---
def find_button_by_color():
    """
    Scans the screen for blobs of the specific #5f8bd9 blue.
    If it finds a blob shaped like a button, it returns the center coordinates.
    NO IMAGE FILE REQUIRED!
    """
    try:
        # 1. Take a screenshot
        screen_pil = ImageGrab.grab()
        screen_bgr = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)

        # 2. Convert to HSV color space for accurate color filtering
        hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

        # 3. Define the exact blue range for #5f8bd9
        # This will strictly catch the active button and completely ignore grey ones
        lower_blue = np.array([95, 80, 100])
        upper_blue = np.array([125, 255, 255])

        # 4. Create a black & white mask (White = Target Blue, Black = Everything else)
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # 5. Find the outlines of all the blue blobs on the screen
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_center = None
        largest_area = 0

        # 6. Check every blue blob we found
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            # Prevent division by zero
            if h == 0: continue
            aspect_ratio = w / float(h)

            # --- THE BUTTON RULES ---
            # Rule 1: A button is wider than it is tall (Ratio usually between 1.5 and 5.0)
            # Rule 2: It must be big enough to actually be a button (Area > 500 pixels)
            # Rule 3: It shouldn't be massive like a header bar (Area < 30000 pixels)
            if 1.5 < aspect_ratio < 5.0 and 500 < area < 30000:

                # If there are multiple valid blue blobs, we assume the largest one is our target
                if area > largest_area:
                    largest_area = area
                    # Calculate the dead-center of this rectangle
                    best_center = (x + (w // 2), y + (h // 2))

        if best_center:
            return best_center, f"Found Blue Button! (Size: {largest_area}px)"
        else:
            return None, "No blue button shapes found on screen."

    except Exception as e:
        print(f"Vision error: {e}")
        return None, "System Error during scan"


# ==========================================
# USER INTERFACE SETUP
# ==========================================
sg.theme('LightGrey1')

layout = [
    [sg.Text("DYPA Auto-Next Bot (Template-Free)", font=("Arial", 14, "bold"), justification='center', expand_x=True)],
    [sg.HSeparator()],
    [sg.Text("Status:"), sg.Text("Waiting to start...", key="-STATUS-", text_color="blue", font=("Arial", 10, "bold"))],
    [sg.Text("Vision Log:"), sg.Text("---", key="-LOG-", text_color="purple", font=("Arial", 9))],
    [sg.Text("Next click in:"), sg.Text("00:00", key="-TIMER-", font=("Arial", 20, "bold"))],
    [sg.Text("Emergency Stop: Press the 'ESC' key anytime", font=("Arial", 8, "italic"), text_color="gray")],
    [sg.HSeparator()],
    [sg.Button("Start Bot", size=(12, 1), button_color="green"), sg.Button("Stop Bot", size=(12, 1)),
     sg.Button("Test Detection", size=(12, 1), button_color="blue")],
    [sg.Button("Exit", button_color="red", expand_x=True)]
]

window = sg.Window("Επόμενο Autoclicker", layout, keep_on_top=True, element_justification='c')

bot_active = False
time_remaining = 0
last_time = time.time()

# ==========================================
# MAIN APPLICATION LOOP
# ==========================================
while True:
    event, values = window.read(timeout=100)

    if keyboard.is_pressed('esc'):
        print("Emergency Stop triggered via ESC key!")
        break

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    # --- TEST BUTTON LOGIC ---
    if event == "Test Detection":
        window["-STATUS-"].update("Scanning screen...", text_color="orange")
        window.refresh()

        # Call the new template-free detector
        final_location, log_message = find_button_by_color()
        window["-LOG-"].update(log_message)

        if final_location is not None:
            window["-STATUS-"].update("Test: Target Acquired!", text_color="green")
            pyautogui.moveTo(final_location, duration=0.5)
            # Click is removed during test so it doesn't actually jump the page while you test
            # But you will see the mouse snap right to the center of the blue blob!
            print(f"Mouse moved to: {final_location}")
        else:
            window["-STATUS-"].update("Test: Using Fallback Coords", text_color="orange")
            pyautogui.moveTo(TARGET_COORDINATES, duration=0.5)

    # --- START/STOP BUTTONS ---
    if event == "Start Bot":
        bot_active = True
        time_remaining = get_random_delay()
        window["-STATUS-"].update("Running...", text_color="green")
        window["-TIMER-"].update(format_time(time_remaining))
        last_time = time.time()

    if event == "Stop Bot":
        bot_active = False
        window["-STATUS-"].update("Stopped", text_color="red")
        window["-TIMER-"].update("00:00")

    # --- COUNTDOWN & CLICK LOGIC ---
    if bot_active:
        current_time = time.time()

        if current_time - last_time >= 1:
            last_time = current_time
            time_remaining -= 1
            window["-TIMER-"].update(format_time(time_remaining))

            if time_remaining <= 0:
                window["-STATUS-"].update("Scanning...", text_color="orange")
                window.refresh()

                final_location, log_message = find_button_by_color()
                window["-LOG-"].update(log_message)

                if final_location is None:
                    final_location = TARGET_COORDINATES

                if final_location:
                    pyautogui.moveTo(final_location, duration=0.5)
                    pyautogui.click()  # Actually click during the live bot run
                    window["-STATUS-"].update("Clicked! Waiting for next...", text_color="green")
                    time_remaining = get_random_delay()
                else:
                    window["-STATUS-"].update("Error! Retrying in 5s.", text_color="red")
                    time_remaining = 5

                window["-TIMER-"].update(format_time(time_remaining))

window.close()