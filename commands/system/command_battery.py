import psutil
from core.audio.voice_utils import speak

def battery_status():
    try:
        battery = psutil.sensors_battery()
        percent = battery.percent
        plugged = battery.power_plugged
        speak(f"Battery is at {percent} percent.")
        speak("Charger is plugged in." if plugged else "Charger is not plugged in.")
    except Exception:
        speak("Failed to get battery status.")
