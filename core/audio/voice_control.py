import speech_recognition as sr


def take_command(ui=None):
    r = sr.Recognizer()
    r.energy_threshold = 120
    r.dynamic_energy_threshold = True
    r.dynamic_energy_adjustment_damping = 0.15
    r.pause_threshold = 0.5

    # Auto-detect a working microphone; fall back to system default
    mic_index = None
    try:
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            if "Microphone" in name or "microphone" in name:
                mic_index = i
                break
    except Exception:
        mic_index = None  # Silently use system default

    try:
        with sr.Microphone(device_index=mic_index) as source:
            r.adjust_for_ambient_noise(source, duration=0.5)

            if ui:
                ui.set_state("LISTENING")
                ui.set_subtitle("Listening...")
                ui.clear_message()

            audio = r.listen(source, timeout=5, phrase_time_limit=8)

    except OSError:
        # Stream conflict — retry once with system default mic
        try:
            with sr.Microphone(device_index=None) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
        except Exception as e:
            print(f"[Mic Fallback Error] {e}")
            if ui:
                ui.set_state("IDLE")
                ui.set_subtitle("Microphone unavailable")
            return ""

    except sr.WaitTimeoutError:
        # User didn't speak within timeout
        return ""

    except Exception as e:
        print(f"[Microphone Error] {e}")
        if ui:
            ui.set_state("IDLE")
            ui.set_subtitle("Microphone unavailable")
        return ""

    try:
        query = r.recognize_google(audio, language="en-in").lower()

        if ui:
            ui.set_subtitle(f'Captured: "{query}"')
            ui.set_message(f"You: {query}", "#a0b0d0")
            # We don't clear the subtitle immediately so the user can read it

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