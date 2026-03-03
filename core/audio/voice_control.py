
import speech_recognition as sr
from core.audio.voice_engine import speak

def take_command(ui=None):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if ui: ui.set_state("LISTENING")
        audio = r.listen(source)
    try:
        query = r.recognize_google(audio, language='en-in').lower()
        if ui: ui.set_state("IDLE")
        return query
    except Exception:
        if ui: ui.set_state("IDLE")
        return ""
