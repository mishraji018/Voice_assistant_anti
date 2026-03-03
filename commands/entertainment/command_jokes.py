import pyjokes
from core.audio.voice_utils import speak

def tell_joke():
    joke = pyjokes.get_joke()
    speak(joke)
