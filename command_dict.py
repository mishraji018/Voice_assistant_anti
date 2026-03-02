from PyDictionary import PyDictionary
from voice_utils import speak

def define_word(word):
    try:
        dictionary = PyDictionary()
        meaning = dictionary.meaning(word)
        if meaning:
            for pos, defs in meaning.items():
                speak(f"{pos}: {defs[0]}")
        else:
            speak("Could not find the definition.")
    except Exception:
        speak("Failed to get the definition.")
