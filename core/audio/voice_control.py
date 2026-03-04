
import speech_recognition as sr
from core.audio.voice_engine import speak

def take_command(ui=None):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if ui:
            ui.set_state("LISTENING")
            ui.set_subtitle("Listening...")
            ui.clear_message()
        audio = r.listen(source)
    try:
        query = r.recognize_google(audio, language='en-in').lower()
        # Show user text IMMEDIATELY in persistent message box (won't flicker)
        if ui:
            ui.set_message(f"You: {query}", "#a0b0d0")
            ui.set_subtitle("")
        return query
    except Exception:
        if ui:
            ui.set_state("IDLE")
            ui.set_subtitle("")
        return ""
