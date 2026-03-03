def run(command_text: str) -> str:
    """Standardized entry point for weather command."""
    # Basic city extraction logic
    city = "Delhi"
    # Simple search for "in [City]" or "[City] weather"
    m = re.search(r"in\s+([a-zA-Z\s]+)", command_text, re.IGNORECASE)
    if m:
        city = m.group(1).strip()
    
    return get_weather_data(city)

def get_weather_data(city="Delhi"):
    api_key = "YOUR_API_KEY"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        # Note: In a real scenario, YOUR_API_KEY must be valid
        # For now, we return a fallback or the actual data if possible
        return f"Fetching weather for {city}..."
    except Exception:
        return "Failed to get weather info."
import re
