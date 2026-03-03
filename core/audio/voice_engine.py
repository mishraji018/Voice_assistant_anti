"""
voice_engine.py  –  Neural TTS Engine for Jarvis
=================================================
Provides a warm, natural AI voice using Microsoft Edge Neural TTS
(edge-tts) as the primary engine, with automatic pyttsx3 fallback.

Architecture
------------
• All speech is non-blocking: pushed onto a queue, played in a
  dedicated daemon thread.  Callers return immediately.
• edge-tts is async; the worker thread runs its own asyncio event loop.
• pyttsx3 is used as a fallback when edge-tts / internet is unavailable.

Voices (best female options, in preference order)
-------------------------------------------------
  en-IN-NeerjaNeural      Indian English, warm, Alexa-like
  en-US-JennyNeural       US English, calm, assistant-like
  en-US-AriaNeural        US English, expressive
  en-IN-PriyaNeural       Indian English, friendly
  en-GB-SoniaNeural       British English, professional

Public API (drop-in for ResponseManager)
----------------------------------------
    from voice_engine import SpeechEngine

    se = SpeechEngine()
    se.speak("Hello! How can I help you?")       # non-blocking
    se.speak("Opening YouTube…", jarvis=True)    # slightly different tone
    se.wait_until_done()                         # block until queue empty
    se.shutdown()                                # clean exit
"""

from __future__ import annotations

import asyncio
import io
import os
import queue
import threading
import time
import tempfile
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Preferred voice roster (tried in order; first available wins)
# ─────────────────────────────────────────────────────────────────────────────

_PREFERRED_VOICES = [
    "en-IN-NeerjaNeural",  # Indian English – warm, Alexa-like ← default
    "en-US-JennyNeural",   # US, calm assistant
    "en-US-AriaNeural",    # US, expressive
    "en-IN-PriyaNeural",   # Indian English, friendly
    "en-GB-SoniaNeural",   # British English, clear
]

# Jarvis (secondary) voice — slightly deeper/different for confirmations
_JARVIS_VOICE = "en-IN-NeerjaNeural"   # same family, adjusted rate

# Speech parameters
_DEFAULT_RATE   = "-5%"     # slightly slower than default (natural pacing)
_JARVIS_RATE    = "+0%"     # normal rate for Jarvis confirmations
_DEFAULT_VOLUME = "+0%"     # 100% volume

# Sentinel to stop the worker thread
_STOP = object()


# ─────────────────────────────────────────────────────────────────────────────
# Probe: pick the first reachable edge-tts voice
# ─────────────────────────────────────────────────────────────────────────────

def _pick_edge_voice() -> Optional[str]:
    """
    Try to list edge-tts voices to confirm network + library are available.
    Returns the first preferred voice found, or None if unavailable.
    """
    try:
        import edge_tts

        async def _list():
            return await edge_tts.list_voices()

        loop = asyncio.new_event_loop()
        voices = loop.run_until_complete(_list())
        loop.close()

        available = {v["ShortName"] for v in voices}
        for pref in _PREFERRED_VOICES:
            if pref in available:
                print(f"[VoiceEngine] ✓ Edge-TTS voice selected: {pref}")
                return pref
        # If none of our preferred voices exist, take first English female
        for v in voices:
            if v.get("Gender") == "Female" and v["Locale"].startswith("en-"):
                print(f"[VoiceEngine] ✓ Edge-TTS fallback voice: {v['ShortName']}")
                return v["ShortName"]
    except Exception as exc:
        print(f"[VoiceEngine] edge-tts unavailable ({exc}), using pyttsx3.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# pyttsx3 fallback: auto-select best female system voice
# ─────────────────────────────────────────────────────────────────────────────

def _best_pyttsx3_voice(engine):
    """
    Auto-select the best female voice available via pyttsx3.
    Priority: voices with 'Zira', 'Aria', 'Jenny', 'female', 'woman' in name.
    Falls back to first available voice.
    Returns the voice id.
    """
    voices = engine.getProperty("voices")
    if not voices:
        return None

    print("\n[VoiceEngine] Available pyttsx3 voices:")
    for i, v in enumerate(voices):
        print(f"  [{i}] {v.name}  (id: {v.id})")

    # Preference keywords in voice name (case-insensitive)
    female_hints = ["zira", "aria", "jenny", "hazel", "susan", "female",
                    "woman", "girl", "neerja", "priya", "heera"]

    for hint in female_hints:
        for v in voices:
            if hint in v.name.lower():
                print(f"[VoiceEngine] ✓ pyttsx3 selected: {v.name}")
                return v.id

    # Last resort — pick second voice if exists (first is often male on Windows)
    selected = voices[1] if len(voices) > 1 else voices[0]
    print(f"[VoiceEngine] ✓ pyttsx3 fallback: {selected.name}")
    return selected.id


# ─────────────────────────────────────────────────────────────────────────────
# SpeechEngine
# ─────────────────────────────────────────────────────────────────────────────

class SpeechEngine:
    """
    Drop-in replacement for pyttsx3 speech in ResponseManager.

    Uses Microsoft Edge Neural TTS (edge-tts) when online,
    falls back to pyttsx3 with best female voice when offline.

    All speech is non-blocking (fire-and-forget from caller's perspective).
    """

    def __init__(self, rate: str = _DEFAULT_RATE, volume: str = _DEFAULT_VOLUME):
        self._rate   = rate
        self._volume = volume
        self._q      = queue.Queue()

        # Events for synchronization (mirrors ResponseManager interface)
        self._speaking = threading.Event()   # SET while audio plays
        self._done     = threading.Event()   # SET when queue is empty + idle
        self._done.set()

        # Probe edge-tts; fall back to pyttsx3 if unavailable
        self._edge_voice = _pick_edge_voice()
        self._use_edge   = self._edge_voice is not None

        # Start the background speech worker
        self._worker = threading.Thread(
            target=self._run_worker,
            name="JarvisVoice",
            daemon=True,
        )
        self._worker.start()
        mode = f"edge-tts ({self._edge_voice})" if self._use_edge else "pyttsx3 (fallback)"
        print(f"[VoiceEngine] Started in {mode} mode.")

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str, jarvis: bool = False) -> None:
        """
        Queue text for speech output. Returns immediately (non-blocking).

        Parameters
        ----------
        text   : The text to speak.
        jarvis : If True, use deeper/faster Jarvis-confirmation style.
        """
        if not text or not text.strip():
            return
        print(f"[Voice] {'Jarvis' if jarvis else 'Assistant'}: {text}")
        self._done.clear()
        self._q.put({"text": text, "jarvis": jarvis})

    def wait_until_done(self, timeout: float = 10.0) -> None:
        """
        Block the caller until all queued speech has finished playing.
        Use this before opening the microphone to prevent audio driver conflicts.

        Example:
            se.speak("I'm listening. Go ahead.")
            se.wait_until_done()    # ← mic is safe to open now
            result = listen()
        """
        self._done.wait(timeout=timeout)

    @property
    def is_speaking(self) -> bool:
        """True while audio is actively playing."""
        return self._speaking.is_set()

    def list_edge_voices(self) -> list[dict]:
        """Return all available edge-tts voices (requires internet)."""
        try:
            import edge_tts
            async def _list():
                return await edge_tts.list_voices()
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_list())
            loop.close()
            return result
        except Exception as exc:
            print(f"[VoiceEngine] Could not list voices: {exc}")
            return []

    def shutdown(self) -> None:
        """Stop the speech worker thread cleanly."""
        self._q.put(_STOP)

    # ── Worker thread ─────────────────────────────────────────────────────────

    def _run_worker(self) -> None:
        """Dedicated daemon thread — drains the speech queue one item at a time."""
        # If using pyttsx3 fallback, create engine once (not thread-safe across threads)
        if not self._use_edge:
            self._init_pyttsx3_worker()

        while True:
            item = self._q.get()
            if item is _STOP:
                break

            text  = item["text"]
            jarvis = item["jarvis"]

            self._speaking.set()
            self._done.clear()

            try:
                if self._use_edge:
                    self._speak_edge(text, jarvis)
                else:
                    self._speak_pyttsx3(text, jarvis)
            except Exception as exc:
                print(f"[VoiceEngine] Speech failed: {exc}")
                # Try pyttsx3 as emergency fallback
                try:
                    self._emergency_pyttsx3(text)
                except Exception:
                    pass
            finally:
                try:
                    self._q.task_done()
                except Exception:
                    pass
                self._speaking.clear()
                if self._q.empty():
                    self._done.set()

    # ── edge-tts sub-system ───────────────────────────────────────────────────

    def _speak_edge(self, text: str, jarvis: bool) -> None:
        """
        Speak text using edge-tts neural voice.
        Runs asyncio in the worker thread, saves to a temp MP3, plays via
        Windows Media Player CLI or pygame — no extra GUI/app opens.
        """
        import edge_tts

        voice = self._edge_voice
        rate  = _JARVIS_RATE if jarvis else self._rate

        async def _generate():
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await communicate.save(tmp_path)
            return tmp_path

        loop = asyncio.new_event_loop()
        try:
            tmp_path = loop.run_until_complete(_generate())
        finally:
            loop.close()

        # Play the MP3 using Windows built-in media player (no popup)
        self._play_audio_file(tmp_path)

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    def _play_audio_file(self, path: str) -> None:
        """
        Play an audio file synchronously using the best available method.
        Priority: pygame (most reliable) → PowerShell Media.SoundPlayer (WAV only,
        limited) → os.startfile (opens app, last resort).
        """
        # Method 1: pygame (best — no window, blocks cleanly)
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            return
        except Exception:
            pass

        # Method 2: playsound (cross-platform, simple)
        try:
            import playsound as _ps
            _ps.playsound(path, block=True)
            return
        except Exception:
            pass

        # Method 3: PowerShell WMPlayer (Windows, no window popup)
        try:
            import subprocess
            ps_cmd = (
                f"(New-Object Media.SoundPlayer).Stop(); "
                f"$wmp = New-Object -ComObject WMPlayer.OCX; "
                f"$wmp.URL = '{path}'; "
                f"$wmp.controls.play(); "
                f"Start-Sleep -Seconds 60"
            )
            proc = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            # Wait for estimated audio duration
            size = os.path.getsize(path)
            est_seconds = max(2.0, size / 16000)   # rough: 128kbps MP3
            time.sleep(est_seconds)
            proc.terminate()
            return
        except Exception:
            pass

        # Last resort: tell user, silent failure
        print(f"[VoiceEngine] ⚠ Could not play audio. Text was: ...")

    # ── pyttsx3 sub-system ────────────────────────────────────────────────────

    def _init_pyttsx3_worker(self) -> None:
        """Initialize pyttsx3 engine in the worker thread."""
        try:
            import pyttsx3
            self._px_engine = pyttsx3.init()
            self._px_engine.setProperty("rate", 165)
            self._px_engine.setProperty("volume", 0.95)
            # Auto-select best female voice
            vid = _best_pyttsx3_voice(self._px_engine)
            if vid:
                self._px_engine.setProperty("voice", vid)
        except Exception as exc:
            print(f"[VoiceEngine] pyttsx3 init failed: {exc}")
            self._px_engine = None

    def _speak_pyttsx3(self, text: str, jarvis: bool) -> None:
        """Speak using pyttsx3 (fallback path)."""
        if not hasattr(self, "_px_engine") or self._px_engine is None:
            self._init_pyttsx3_worker()
        if self._px_engine:
            rate = 175 if jarvis else 165
            self._px_engine.setProperty("rate", rate)
            self._px_engine.say(text)
            self._px_engine.runAndWait()

    def _emergency_pyttsx3(self, text: str) -> None:
        """Emergency fallback: fresh pyttsx3 engine from scratch."""
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", 160)
            eng.say(text)
            eng.runAndWait()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Pygame install helper
# ─────────────────────────────────────────────────────────────────────────────

def ensure_pygame() -> bool:
    """Try to import pygame; offer install hint if missing."""
    try:
        import pygame
        return True
    except ImportError:
        print("[VoiceEngine] pygame not found. Install with: pip install pygame")
        print("[VoiceEngine] edge-tts will use PowerShell fallback until then.")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_engine: Optional[SpeechEngine] = None


def get_engine() -> SpeechEngine:
    """Return or create the module-level SpeechEngine singleton."""
    global _engine
    if _engine is None:
        _engine = SpeechEngine()
    return _engine


def speak(text: str, jarvis: bool = False) -> None:
    """Module-level shortcut. Non-blocking."""
    get_engine().speak(text, jarvis=jarvis)


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo / voice listing
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    engine = SpeechEngine()

    if "--list" in sys.argv:
        print("\n── Available edge-tts voices (English, Female) ──")
        for v in engine.list_edge_voices():
            if v.get("Gender") == "Female" and v["Locale"].startswith("en-"):
                print(f"  {v['ShortName']:35} | {v['LocalName']}")
        engine.shutdown()
        sys.exit(0)

    ensure_pygame()

    TESTS = [
        ("Hello! I am Jarvis, your personal AI assistant.", False),
        ("Opening YouTube for you.", False),
        ("Done. What else can I do for you?", True),
        ("The current time is 11:40 AM.", False),
    ]

    print("\nVoice Engine Demo — speaking test phrases…")
    for text, jarvis in TESTS:
        engine.speak(text, jarvis=jarvis)
        engine.wait_until_done()
        time.sleep(0.3)

    engine.shutdown()
    print("Done.")
