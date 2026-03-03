from core.audio.voice_utils import speak
from googletrans import Translator

def translate_text(text, dest_lang='hi'):
    try:
        translator = Translator()
        result = translator.translate(text, dest=dest_lang)
        speak(f"The translation in {dest_lang} is: {result.text}")
    except Exception:
        speak("Failed to translate the text.")
