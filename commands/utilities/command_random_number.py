import random
from core.audio.voice_utils import speak

def random_number(start=1, end=100):
    number = random.randint(start, end)
    speak(f"Your random number is {number}")
