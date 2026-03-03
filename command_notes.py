from voice_utils import speak, take_command

def take_note():
    speak("What would you like to note?")
    note = take_command()
    if note:
        with open("notes.txt", "a") as f:
            f.write(note + "\n")
        speak("Note saved.")
    else:
        speak("No note received.")
