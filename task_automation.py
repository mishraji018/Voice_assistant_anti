import webbrowser
import subprocess
import datetime
import wikipedia
import os

def system_control(command, speak):
    if "shutdown" in command:
        speak("Shutting down the system.")
        os.system("shutdown /s /t 1")
    elif "restart" in command:
        speak("Restarting the system.")
        os.system("shutdown /r /t 1")
    elif "lock" in command:
        speak("Locking the system.")
        os.system("rundll32.exe user32.dll,LockWorkStation")

def do_task(query, speak):
    if 'wikipedia' in query:
        speak("Checking Wikipedia...")
        query = query.replace("wikipedia", "")
        try:
            result = wikipedia.summary(query, sentences=2)
            speak("According to Wikipedia:")
            speak(result)
        except Exception:
            speak("Could not find relevant information on Wikipedia.")
    elif 'youtube' in query:
        webbrowser.open("youtube.com")
        speak("Opening YouTube...")
    elif 'google' in query:
        webbrowser.open("google.com")
        speak("Opening Google...")
    elif 'time' in query:
        time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The time is {time}")
    elif 'open notepad' in query:
        subprocess.Popen('notepad.exe')
        speak("Opening Notepad.")
    elif 'shutdown' in query or 'restart' in query or 'lock' in query:
        system_control(query, speak)
    else:
        speak("I didn't understand that command.")
