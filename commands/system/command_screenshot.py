import pyautogui
from datetime import datetime
from core.audio.voice_utils import speak

def take_screenshot():
    try:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        speak(f"Screenshot taken and saved as {filename}.")
    except Exception:
        speak("Failed to take screenshot.")
