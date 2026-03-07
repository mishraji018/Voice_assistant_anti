import threading
import os
from pathlib import Path

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

_lock = threading.Lock()


def _init_engine():
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 is not installed")
    if os.name == "nt":
        cache_dir = Path(__file__).resolve().parents[2] / ".tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("COMTYPES_CACHE", str(cache_dir))
        try:
            import comtypes.client  # type: ignore
            comtypes.client.gen_dir = str(cache_dir)
        except Exception:
            pass
    return pyttsx3.init()


def speak(text: str, ui=None):
    if not text: return
    if pyttsx3 is None:
        print(f"[TTS Disabled] {text}")
        return
    with _lock:
        try:
            engine = _init_engine()
        except Exception:
            print(f"[TTS Disabled] {text}")
            return
        if ui: ui.set_state("SPEAKING")
        engine.say(text)
        engine.runAndWait()
        if ui: ui.set_state("IDLE")
