import pywhatkit
from voice_utils import speak

def search_youtube(query):
    try:
        speak(f"Searching YouTube for {query}")
        pywhatkit.playonyt(query)
        speak("Playing on YouTube.")
    except Exception:
        speak("Failed to play YouTube video.")
