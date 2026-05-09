import FreeSimpleGUI as sg
import pyautogui
import easyocr
import numpy as np
from PIL import ImageGrab
import time
import random

# 1. Initialize OCR for Greek ('el').
# We include 'en' just in case the system mixes up character sets.
print("Loading OCR Engine (Greek & English)...")
reader = easyocr.Reader(['el', 'en'], gpu=False)


# Helper function to get random seconds between 5:30 and 9:10
def get_random_delay():
    # 5 mins 30 secs = 330 seconds
    # 9 mins 10 secs = 550 seconds
    return random.randint(330, 550)


# Helper function to format seconds into MM:SS for the UI
def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


# 2. Define the UI Layout
layout = [
    [sg.Text("Status:"), sg.Text("Waiting...", key="-STATUS-", text_color="yellow")],
    [sg.Text("Next scan in:"), sg.Text("00:00", key="-TIMER-", font=("Arial", 16, "bold"))],
    [sg.HSeparator()],
    [sg.Button("Start Bot"), sg.Button("Stop Bot")],
    [sg.Button("Exit", button_color="red")]
]

window = sg.Window("Επόμενο Autoclicker", layout, keep_on_top=True)

# State Variables
bot_active = False
time_remaining = 0
last_time = time.time()

# 3. The Main Loop
while True:
    event, values = window.read(timeout=100)

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    if event == "Start Bot":
        bot_active = True
        time_remaining = get_random_delay()  # Get the first random countdown
        window["-STATUS-"].update("Running...", text_color="green")
        window["-TIMER-"].update(format_time(time_remaining))
        last_time = time.time()

    if event == "Stop Bot":
        bot_active = False
        window["-STATUS-"].update("Stopped", text_color="red")
        window["-TIMER-"].update("00:00")

    # 4. Countdown and Scan Logic
    if bot_active:
        current_time = time.time()

        # If one second has passed
        if current_time - last_time >= 1:
            last_time = current_time
            time_remaining -= 1
            window["-TIMER-"].update(format_time(time_remaining))

            # When the countdown hits 0, it's time to scan and click!
            if time_remaining <= 0:
                window["-STATUS-"].update("Scanning screen...", text_color="orange")
                window.refresh()  # Force UI to update immediately

                # Take a full screenshot
                screenshot = ImageGrab.grab()
                img_np = np.array(screenshot)

                # Read text and their bounding boxes.
                # detail=1 returns [([x,y coordinates], 'text', confidence_level)]
                results = reader.readtext(img_np, detail=1)

                button_found = False

                for (bbox, text, prob) in results:
                    # Make it lowercase to ensure it matches regardless of capitalization
                    if "επόμενο" in text.lower():
                        # bbox gives us 4 corners of the text box.
                        # We calculate the center to click it safely.
                        top_left = bbox[0]
                        bottom_right = bbox[2]

                        center_x = int((top_left[0] + bottom_right[0]) / 2)
                        center_y = int((top_left[1] + bottom_right[1]) / 2)

                        pyautogui.click(center_x, center_y)
                        button_found = True
                        break  # Stop looking once we've clicked it

                # Reset for the next cycle
                if button_found:
                    window["-STATUS-"].update("Clicked! Waiting for next...", text_color="green")
                    time_remaining = get_random_delay()
                else:
                    # If it couldn't find the button, try again in 10 seconds
                    # instead of waiting 5-9 minutes again.
                    window["-STATUS-"].update("Not found! Retrying in 10s.", text_color="red")
                    time_remaining = 10

                window["-TIMER-"].update(format_time(time_remaining))

window.close()