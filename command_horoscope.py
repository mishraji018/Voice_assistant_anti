import requests
from voice_utils import speak

def get_horoscope(sign='aries'):
    try:
        url = f"https://ohmanda.com/api/horoscope/{sign}"
        response = requests.get(url)
        data = response.json()
        horoscope = data.get("horoscope", "No horoscope found.")
        speak(f"Horoscope for {sign}: {horoscope}")
    except Exception:
        speak("Failed to fetch your horoscope.")
