from core.audio.voice_utils import speak

TODO_FILE = "todo.txt"

def add_todo(item):
    with open(TODO_FILE, "a") as f:
        f.write(item + "\n")
    speak(f"Task added: {item}")

def list_todos():
    try:
        with open(TODO_FILE, "r") as f:
            tasks = f.readlines()
        if tasks:
            speak("Your to-do list:")
            for i, task in enumerate(tasks, 1):
                speak(f"Task {i}: {task.strip()}")
        else:
            speak("Your to-do list is empty.")
    except FileNotFoundError:
        speak("You have no to-do items.")
