from voice_utils import speak

def calculate(expression):
    try:
        result = eval(expression)
        speak(f"The result is {result}")
    except Exception:
        speak("Sorry, I couldn't calculate that.")
