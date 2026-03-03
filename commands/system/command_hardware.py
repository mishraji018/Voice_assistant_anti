import os
from core.audio.voice_utils import speak

def wifi_control(turn_on=True):
    try:
        if turn_on:
            os.system("netsh interface set interface Wi-Fi enabled")
            speak("WiFi turned ON.")
        else:
            os.system("netsh interface set interface Wi-Fi disabled")
            speak("WiFi turned OFF.")
    except Exception:
        speak("Failed to control WiFi.")

# Add more hardware controls (brightness, Bluetooth, etc.) as needed.
