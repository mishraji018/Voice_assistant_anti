import os
from core.audio.voice_utils import speak

def bluetooth_control(turn_on=True):
    try:
        if turn_on:
            os.system("PowerShell Start-Service bthserv")
            speak("Bluetooth turned ON.")
        else:
            os.system("PowerShell Stop-Service bthserv")
            speak("Bluetooth turned OFF.")
    except Exception:
        speak("Failed to control Bluetooth.")
