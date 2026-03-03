import requests
from voice_utils import speak

def get_weather(city="Delhi"):
    api_key = "YOUR_API_KEY"  # Get one from openweathermap.org
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data["cod"] != "404":
            weather = data["main"]
            temperature = weather["temp"]
            desc = data["weather"][0]["description"]
            speak(f"The temperature in {city} is {temperature}°C and the weather is {desc}.")
        else:
            speak("City not found.")
    except Exception:
        speak("Failed to get weather info.")
