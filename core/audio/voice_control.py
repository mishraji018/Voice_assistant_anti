import speech_recognition as sr
from core.audio.voice_engine import speak


def take_command(ui=None):
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.pause_threshold = 0.8 
    try:
        # Auto-detect a working microphone
        mic_index = None
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            if "Microphone" in name:
                mic_index = i
                break

        with sr.Microphone(device_index=mic_index) as source:

            # Reduce noise problems
            r.adjust_for_ambient_noise(source, duration=1)

            if ui:
                ui.set_state("LISTENING")
                ui.set_subtitle("Listening...")
                ui.clear_message()

            audio = r.listen(source, timeout=5, phrase_time_limit=8)

    except Exception as e:
        print("Microphone error:", e)  # helpful for debugging
        if ui:
            ui.set_state("IDLE")
            ui.set_subtitle("Microphone unavailable")
        return ""

    try:
        query = r.recognize_google(audio, language="en-in").lower()

        if ui:
            ui.set_message(f"You: {query}", "#a0b0d0")
            ui.set_subtitle("")

        return query

    except sr.UnknownValueError:
        if ui:
            ui.set_state("IDLE")
            ui.set_subtitle("Didn't catch that")
        return ""

    except sr.RequestError:
        if ui:
            ui.set_state("IDLE")
            ui.set_subtitle("Speech service unavailable")
        return ""