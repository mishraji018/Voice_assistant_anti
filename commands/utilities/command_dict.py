import requests
from core.audio.voice_utils import speak

def define_word(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if isinstance(data, list) and data:
            meanings = data[0].get("meanings", [])
            for meaning in meanings[:2]:
                pos = meaning.get("partOfSpeech", "")
                defs = meaning.get("definitions", [])
                if defs:
                    speak(f"{pos}: {defs[0]['definition']}")
        else:
            speak("Could not find the definition.")
    except Exception:
        speak("Failed to get the definition.")
