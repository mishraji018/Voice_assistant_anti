# command_notes.py
# Handles saving notes spoken by the user

import datetime

NOTES_FILE = "jarvis_notes.txt"

def take_note(text=None, speak_fn=None):
    """
    Save a note to file.
    text: note content (string)
    speak_fn: optional TTS function
    """

    if not text:
        if speak_fn:
            speak_fn("What should I write in the note?")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")

        if speak_fn:
            speak_fn("Note saved successfully.")

        print("[Notes] Saved:", text)

    except Exception as e:
        if speak_fn:
            speak_fn("Sorry, I couldn't save the note.")
        print("[Notes Error]", e)