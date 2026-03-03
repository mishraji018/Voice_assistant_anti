import speech_recognition as sr
import pyttsx3
import webbrowser
import datetime

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def take_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
    try:
        query = r.recognize_google(audio, language='en-in')
        return query.lower()
    except Exception as e:
        return ""

speak("How can I help you?")
while True:
    command = take_command()
    if 'youtube' in command:
        webbrowser.open("youtube.com")
        speak("Opening YouTube")
    elif 'time' in command:
        now = datetime.datetime.now().strftime("%H:%M")
        speak(f"The time is {now}")
    elif 'exit' in command:
        speak("Goodbye.")
        break
