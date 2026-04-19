import threading
import os
import asyncio
import tempfile
import hashlib
import queue
import ctypes
import time
from pathlib import Path

import edge_tts
import playsound

# ── ElevenLabs ────────────────────────────────────────────────
try:
    from elevenlabs.client import ElevenLabs
    try:
        from elevenlabs.play import play
    except ImportError:
        from elevenlabs import play
    
    _eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    _ELEVEN_AVAILABLE = True
except Exception as e:
    _ELEVEN_AVAILABLE = False
    print(f"[TTS] ElevenLabs disabled by default: {e}")

# Keep track of voice IDs that don't exist in the current account to avoid repeated lag
_BROKEN_VOICE_IDS = set()

# ── Voice settings ─────────────────────────────────────────────
JARVIS_VOICE = "en-IN-PrabhatNeural"   # Backup Indian male
FEMALE_VOICE = "en-IN-NeerjaNeural"    # Assistant voice

ELEVEN_VOICE = "qDuRKMlYmrm8trt5QyBn"  # Taksh (Indian Male) - Powerful & Commanding
ELEVEN_MODEL = "eleven_multilingual_v2" # Best for Hinglish

# ── TTS Cache ─────────────────────────────────────────────────
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / ".tts_cache"
CACHE_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()

def _play_audio(path: str):
    """Robust playback for Windows using MCI strings."""
    if not os.path.exists(path):
        print(f"[Playback Error] File not found: {path}", flush=True)
        return

    path = os.path.abspath(path)
    # Using a unique alias for this playback session
    alias = f"audio_{int(time.time() * 1000)}"
    
    try:
        # MCI Commands for Windows
        ctypes.windll.winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, 0)
        ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
        ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
    except Exception as e:
        print(f"[Playback Error] Native playback failed: {e}. Trying playsound fallback.", flush=True)
        try:
            playsound.playsound(path)
        except Exception as e2:
            print(f"[Playback Error] All methods failed: {e2}", flush=True)

def _speak_elevenlabs(text: str):
    """ElevenLabs TTS with local caching."""
    cache_key = hashlib.md5(text.encode()).hexdigest() + ".mp3"
    cache_path = CACHE_DIR / cache_key

    # Play from cache if already generated
    if cache_path.exists():
        print(f"[SpeechEngine] Playing cached audio: {cache_path}", flush=True)
        _play_audio(str(cache_path))
        return

    # Generate new audio
    response = _eleven_client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE,
        text=text,
        model_id=ELEVEN_MODEL,
        output_format="mp3_22050_32",
    )

    # Convert generator to bytes and save
    audio_bytes = b"".join(response)
    with open(cache_path, "wb") as f:
        f.write(audio_bytes)

    print(f"[SpeechEngine] Playing generated audio: {cache_path}", flush=True)
    _play_audio(str(cache_path))


async def _speak_edge_async(text: str, voice: str):
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate="+5%",
        pitch="-8Hz",
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        audio_path = f.name

    await communicate.save(audio_path)
    print(f"[SpeechEngine] Playing Edge-TTS audio: {audio_path}", flush=True)
    _play_audio(audio_path)

    try:
        os.remove(audio_path)
    except Exception:
        pass


def _speak_sync(text: str, voice: str, jarvis: bool = True):
    # Try ElevenLabs first if it's the Jarvis voice and not marked as broken
    if jarvis and _ELEVEN_AVAILABLE and ELEVEN_VOICE not in _BROKEN_VOICE_IDS:
        try:
            _speak_elevenlabs(text)
            return
        except Exception as e:
            # Check if it's a 404/401
            err_str = str(e).lower()
            if "not_found" in err_str or "404" in err_str or "401" in err_str:
                print(f"[TTS] Voice issue or Auth error. Blacklisting for this session.")
                _BROKEN_VOICE_IDS.add(ELEVEN_VOICE)
            print(f"[TTS] ElevenLabs failed, falling back to Edge: {e}", flush=True)

    # Fallback to Edge TTS
    try:
        asyncio.run(_speak_edge_async(text, voice))
    except RuntimeError:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_speak_edge_async(text, voice))
            loop.close()
        except Exception as e:
            print(f"[TTS Error] {e}", flush=True)


# ══════════════════════════════════════════════════════════════
# SpeechEngine class — response_manager.py yahi use karta hai
# ══════════════════════════════════════════════════════════════

class SpeechEngine:
    """
    Non-blocking Speech Engine.
    Uses a worker thread to handle TTS generation and playback so the UI never lags.
    """
    def __init__(self):
        self._q = queue.Queue()
        self._speaking = False
        self._done_event = threading.Event()
        self._done_event.set()
        
        # Start worker thread
        self._worker = threading.Thread(target=self._speech_worker, name="SpeechWorker", daemon=True)
        self._worker.start()
        
        status = "ElevenLabs Ready" if _ELEVEN_AVAILABLE else "Edge-TTS Fallback"
        print(f"[SpeechEngine] Initialization: {status} (Non-blocking mode).", flush=True)

    def _speech_worker(self):
        """Internal worker to process the speech queue without blocking the main UI."""
        print("[SpeechEngine] Background worker started.", flush=True)
        while True:
            item = self._q.get()
            if item is None: break 
            
            text, jarvis = item
            voice = JARVIS_VOICE if jarvis else FEMALE_VOICE
            print(f"[SpeechEngine] Processing: '{text[:40]}...' (Jarvis={jarvis})", flush=True)
            
            self._speaking = True
            self._done_event.clear()
            
            try:
                with _lock:
                    _speak_sync(text, voice, jarvis=jarvis)
            except Exception as e:
                print(f"[SpeechEngine Worker] CRITICAL ERROR during playback: {e}", flush=True)
            finally:
                self._speaking = False
                self._done_event.set()
                self._q.task_done()
                print("[SpeechEngine] Speech finished processing.", flush=True)

    def speak(self, text: str, jarvis: bool = True) -> None:
        """
        Speak text using the best available engine.
        Returns immediately and processes in the background.
        """
        if not text:
            return
        # Put into queue and return immediately
        self._q.put((text, jarvis))

    def wait_until_done(self, timeout: float = 15.0) -> None:
        """Block the current thread until speech queue is empty."""
        self._done_event.wait(timeout=timeout)

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def shutdown(self) -> None:
        """Gracefully stop the worker thread."""
        self._q.put(None)