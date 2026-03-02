from googlesearch import search
import requests
from bs4 import BeautifulSoup
from voice_utils import speak

def google_search(query):
    try:
        for url in search(query, num_results=1):
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraph = soup.find('p')
            result = paragraph.text if paragraph else "Found the page but could not extract summary."
            speak(result)
            break
    except Exception:
        speak("Failed to search or fetch the result.")
