from datetime import datetime
from core.audio.voice_utils import speak

try:
    import pyautogui
except Exception:
    pyautogui = None

def take_screenshot():
    if pyautogui is None:
        speak("Screenshot feature requires pyautogui.")
        return
    try:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        speak(f"Screenshot taken and saved as {filename}.")
    except Exception:
        speak("Failed to take screenshot.")
