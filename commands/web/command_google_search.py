import webbrowser
import requests
from bs4 import BeautifulSoup
from core.audio.voice_utils import speak

def google_search(query):
    try:
        speak(f"Searching Google for {query}")
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        # Try to get a quick answer from DuckDuckGo instant answer
        ddg_url = f"https://api.duckduckgo.com/?q={query.replace(' ', '+')}&format=json&no_redirect=1"
        response = requests.get(ddg_url, timeout=5)
        data = response.json()
        abstract = data.get("AbstractText", "")
        if abstract:
            speak(abstract[:300])
        else:
            # Fall back to opening the browser
            webbrowser.open(url)
            speak("Opened Google search in your browser.")
    except Exception:
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        speak("Opened Google search in your browser.")
