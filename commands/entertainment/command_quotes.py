import random
from core.audio.voice_utils import speak

QUOTES = [
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "Success is not in what you have, but who you are.",
    "Opportunities don't happen, you create them.",
    "The only way to do great work is to love what you do.",
    "Don't let yesterday take up too much of today."
]

def daily_quote():
    quote = random.choice(QUOTES)
    speak(quote)
