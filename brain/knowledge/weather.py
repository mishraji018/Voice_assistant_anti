
import requests
import os
import logging

logger = logging.getLogger(__name__)

# Note: You can use OpenWeatherMap API or Scraping. 
# Using a clean API approach (OpenWeatherMap) as per ni.env availability.
API_KEY = os.getenv("OPENWEATHER_KEY")

def get_weather(city: str = "Delhi") -> str:
    """Fetch live weather data for a city."""
    if not API_KEY:
        return "Sir, weather API key missing hai. Please check your configuration."
        
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url).json()
        
        if response.get("cod") != 200:
            return f"Sir, mujhe {city} ka mausam nahi mil pa raha hai."
            
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        
        # Professional Hindi-English response
        return f"Sir, {city} mein abhi taapmaan {temp} degree Celsius hai aur wahan {desc} ho rahi hai."
    except Exception as e:
        logger.error(f"Weather Fetch Error: {e}")
        return "Sir, mausam ki jankari lene mein kuch takleef ho rahi hai."

def handle_weather_query(text: str) -> str:
    """Process weather intent and extract city if possible."""
    text = text.lower()
    
    # Simple city extraction logic (can be improved with NER)
    # Common Indian cities or look for "in <city>"
    words = text.split()
    city = "Delhi" # Default
    
    if "in" in words:
        idx = words.index("in")
        if idx + 1 < len(words):
            city = words[idx + 1]
    elif "mein" in words:
        idx = words.index("mein")
        if idx - 1 >= 0:
            city = words[idx - 1]
            
    # If the user just says "weather today", we use default or ask
    if "today" in text or "aaj" in text:
        return get_weather(city)
        
    return get_weather(city)
