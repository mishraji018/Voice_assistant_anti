from voice_utils import speak

def set_reminder(message):
    speak(f"Reminder set: {message}")
    print(f"REMINDER: {message}")  # In a real system, save and check reminders periodically
