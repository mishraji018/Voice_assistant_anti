import pyperclip
from core.audio.voice_utils import speak

def read_clipboard():
    try:
        data = pyperclip.paste()
        if data:
            speak(f"Clipboard contains: {data[:100]}")  # Reads the first 100 chars
        else:
            speak("Clipboard is empty.")
    except Exception:
        speak("Failed to read clipboard.")
