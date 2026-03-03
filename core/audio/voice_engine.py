
import pyttsx3
import threading

_lock = threading.Lock()

def speak(text: str, ui=None):
    if not text: return
    with _lock:
        engine = pyttsx3.init()
        if ui: ui.set_state("SPEAKING")
        engine.say(text)
        engine.runAndWait()
        if ui: ui.set_state("IDLE")
