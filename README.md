# dypa-autoclicker

Desktop Python app for automating repetitive **Next** button clicks in DYPA browser workflows, with color detection, OCR-based progress reading, and a small control panel.

## Features

- GUI built with `FreeSimpleGUI`
- Detects the target button by screen color
- Reads progress numbers with `easyocr`
- Multiple speed profiles: Turbo, Fast, Normal, Slow
- Optional click muting and human-like mouse movement
- Session timer, next-click timer, and estimated finish times
- Test Vision and Sound Test helpers
- Packaging-oriented script variant for EXE use

## Requirements

- Windows
- Python 3.12+ recommended
- A visible DYPA page/workflow on screen

Python dependencies are listed in `requirements.txt`.

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python maincheat.py
```

## How it works

1. The app starts a splash screen and initializes the OCR engine.
2. It searches the screen for a blue button-like area.
3. It captures the progress text area near that button.
4. It reads progress with OCR and estimates remaining time.
5. When started, it clicks the detected button on a configurable schedule.
6. It stops automatically when the session timer expires or when the workflow is near completion.

## Usage

1. Open the target DYPA page and keep it visible on screen.
2. Start the app with `python maincheat.py`.
3. Click **Test Vision** to confirm the button is detected.
4. Choose a speed profile.
5. Optionally enable or disable:
   - **Mute Clicks**
   - **Humanizer Moves**
6. Click **START BOT**.
7. Press **ESC** or use **STOP BOT** to stop the bot.

## Project files

- `maincheat.py` – main application script
- `maincheat-to-exe.py` – packaging-oriented variant
- `requirements.txt` – Python dependencies
- `next_button.png` – image asset in the repository
- `debug_ocr_box.png` – OCR/debug image asset

## Notes

- The application uses `winsound`, so it is intended for Windows.
- `easyocr` may download model files on first run.
- Generated OCR model files are expected under a local `models/` directory.

## Disclaimer

Use this project responsibly and only in environments where automation is allowed.
