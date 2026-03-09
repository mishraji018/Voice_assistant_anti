import threading
import os
from pathlib import Path
import asyncio
import tempfile

import edge_tts
import playsound

_lock = threading.Lock()

VOICE = "en-IN-NeerjaNeural"


async def _speak_async(text: str):
    communicate = edge_tts.Communicate(text, VOICE)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        audio_path = f.name

    await communicate.save(audio_path)
    playsound.playsound(audio_path)

    try:
        os.remove(audio_path)
    except Exception:
        pass


def speak(text: str, ui=None):
    if not text:
        return

    with _lock:
        try:
            if ui:
                ui.set_state("SPEAKING")

            asyncio.run(_speak_async(text))

        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_speak_async(text))

        except Exception:
            print(f"[TTS Error] {text}")

        finally:
            if ui:
                ui.set_state("IDLE")