import requests
from core.audio.voice_utils import speak

def get_news():
    api_key = "YOUR_NEWSAPI_KEY"  # Get it from https://newsapi.org/
    url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}"
    try:
        response = requests.get(url)
        articles = response.json().get("articles")
        if articles:
            speak("Here are the top news headlines:")
            for i, article in enumerate(articles[:5], 1):
                speak(f"Headline {i}: {article['title']}")
        else:
            speak("Sorry, I couldn't find any news.")
    except Exception:
        speak("Failed to get news.")
