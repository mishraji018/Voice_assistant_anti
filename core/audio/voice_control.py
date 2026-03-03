import speech_recognition as sr
import pyttsx3

# Initialize the text-to-speech engine
engine = pyttsx3.init()

def speak(text):
    print("Jarvis:", text)
    engine.say(text)
    engine.runAndWait()

def take_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
    try:
        command = r.recognize_google(audio, language='en-in').lower()
        print("You said:", command)
        return command
    except Exception:
        speak("Sorry, I did not catch that. Please say again.")
        return ""

# Example usage loop
if __name__ == "__main__":
    speak("How can I help you?")
    while True:
        query = take_command()
        if 'exit' in query or 'goodbye' in query:
            speak("Goodbye!")
            break
        elif query:
            speak(f"You said: {query}")
