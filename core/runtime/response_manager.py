import random
import threading
import queue as _queue
import re
import os
from pathlib import Path
from brain.infra.event_bus import bus
from core.state.runtime_state import state

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

# ── Optional: neural voice engine (edge-tts + pygame) ─────────────────────
try:
    from core.audio.voice_engine import SpeechEngine as _SpeechEngine
    _NEURAL_AVAILABLE = True
except Exception as e:
    print(f"[ResponseManager] Neural import failed: {e}")
    _NEURAL_AVAILABLE = False


def _prepare_windows_tts_cache():
    """Use a writable COM type cache location for pyttsx3/comtypes on Windows."""
    if os.name != "nt":
        return
    cache_dir = Path(__file__).resolve().parents[2] / ".tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("COMTYPES_CACHE", str(cache_dir))
    try:
        import comtypes.client  # type: ignore
        comtypes.client.gen_dir = str(cache_dir)
    except Exception:
        # Keep running even if comtypes is unavailable.
        pass


def _init_pyttsx3_engine():
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 is not installed")
    _prepare_windows_tts_cache()
    return pyttsx3.init()

# ---------------------------------------------------------------------------
# Phrase pools
# ---------------------------------------------------------------------------

_PRE_ACTION: dict[str, list[str]] = {
    "OPEN_APP"       : ["Sir, {entity} khol raha hoon...",
                        "Launching {entity}, please wait sir...",
                        "Sir, ek second, {entity} start karta hoon...",
                        "One moment sir — bringing up {entity}..."],

    "CLOSE_WINDOW"   : ["Sir, window band kar raha hoon...",
                        "Shutting it down, sir...",
                        "Ji sir, close kar diya."],

    "SEARCH_WEB"     : ["Sir, {entity} search ho raha hai web par...",
                        "{entity} ke baare mein info laa raha hoon...",
                        "Googling {entity} right now, sir..."],

    "SYSTEM_CONTROL" : ["Sir, system command run kar raha hoon...",
                        "Sir, settings apply ho rahi hain...",
                        "Processing that request, sir..."],

    "MEDIA_CONTROL"  : ["Sir, media play kar raha hoon...",
                        "Starting playback, sir...",
                        "Loading your content..."],

    "INFO_QUERY"     : ["Sir, info dhoond raha hoon...",
                        "Let me check that, sir...",
                        "Looking that up for you, sir..."],

    "NOTE_TASK"      : ["Sir, note save kar raha hoon...",
                        "Reminder set kar raha hoon sir...",
                        "Adding to your list, sir..."],

    "CALCULATOR"     : ["Calculating sir...",
                        "Running the numbers..."],

    "NEWS"           : ["Sir, latest news laa raha hoon...",
                        "Loading your headlines, sir..."],

    "SMALL_TALK"     : [],   # no pre-action for small talk

    "UNKNOWN"        : ["Ji sir, koshish karta hoon...",
                        "Let me try that, sir..."],
}

_POST_ACTION: dict[str, list[str]] = {
    "OPEN_APP"       : ["Sir, {entity} open ho gaya hai.",
                        "{entity} is now running, sir.",
                        "Done! {entity} ready hai.",
                        "I've launched {entity} for you, sir."],

    "CLOSE_WINDOW"   : ["Sir, window band kar di hai.",
                        "Done sir, it's all closed up.",
                        "I've closed that for you, sir."],

    "SEARCH_WEB"     : ["Sir, {entity} ke search results ready hain.",
                        "Results open kar diye hain sir.",
                        "Done! Results dekh lijiye sir."],

    "SYSTEM_CONTROL" : ["Sir, system command successfully execute ho gaya.",
                        "Done sir — your system has been updated.",
                        "All set on the system side, sir."],

    "MEDIA_CONTROL"  : ["Media play ho raha hai sir. Enjoy!",
                        "Done! Hope you enjoy it, sir.",
                        "Playback started, sir."],

    "INFO_QUERY"     : ["Hope that answers your question, sir!",
                        "There you go, sir.",
                        "Sir, yeh info mili hai aapke liye."],

    "NOTE_TASK"      : ["All saved, sir!",
                        "Sir, reminder set ho gaya hai.",
                        "Your task has been noted, sir."],

    "CALCULATOR"     : ["Sir, yeh hai result.",
                        "Calculation complete, sir!"],

    "NEWS"           : ["Sir, yeh rahi latest news. Stay informed!",
                        "Here are your top stories, sir."],

    "SMALL_TALK"     : ["Sir, aapse baat karke hamesha achha lagta hai!",
                        "Good to talk, sir! Kuch aur madad chahiye?"],

    "UNKNOWN"        : ["Sir, maine koshish ki hai.",
                        "Let me know if you need anything else, sir."],
}


def _pick(pool: list[str], entity: str = "") -> str:
    """Select a random phrase and substitute the entity placeholder."""
    if not pool:
        return ""
    phrase = random.choice(pool)
    if entity:
        phrase = phrase.replace("{entity}", entity.title())
    else:
        phrase = phrase.replace("{entity}", "that").replace(" for that", "")
    return phrase


# ---------------------------------------------------------------------------
# Internal speech-queue sentinel
# ---------------------------------------------------------------------------
_STOP_SENTINEL = object()


# ---------------------------------------------------------------------------
# ResponseManager class
# ---------------------------------------------------------------------------

class ResponseManager:
    """
    Manages dual-voice TTS using a single shared pyttsx3 engine.
    Supports streaming (sentence-by-sentence) speech.
    """

    def __init__(self, use_neural: bool = True):
        self._q       = _queue.Queue()
        self._rate    = 185 # Slightly faster for better flow
        self._volume  = 0.95
        self._tts_enabled = pyttsx3 is not None

        self._speaking = threading.Event()
        self._done     = threading.Event()
        self._done.set()

        self._neural = False
        self._se     = None
        if use_neural and _NEURAL_AVAILABLE:
            try:
                self._se     = _SpeechEngine()
                self._neural = True
                print("[ResponseManager] ✓ Neural voice engine active (edge-tts).")
            except Exception as exc:
                print(f"[ResponseManager] Neural voice unavailable ({exc}), using pyttsx3.")

        if not self._neural:
            if pyttsx3 is None:
                self._voices = []
                self._n_voices = 0
                self._jarvis_idx = 0
                self._female_idx = 0
                self._tts_enabled = False
                print("[ResponseManager] pyttsx3 not installed; speech output disabled.")
                return

            try:
                _eng = _init_pyttsx3_engine()
                self._voices = _eng.getProperty('voices')
                self._n_voices = len(self._voices)
                del _eng
            except Exception as exc:
                self._voices = []
                self._n_voices = 0
                self._jarvis_idx = 0
                self._female_idx = 0
                self._tts_enabled = False
                print(f"[ResponseManager] pyttsx3 init failed ({exc}); speech output disabled.")
                return

            self._jarvis_idx = 0
            self._female_idx = 1 if self._n_voices > 1 else 0

            print(f"[ResponseManager] {self._n_voices} pyttsx3 voice(s) found.")

            self._worker = threading.Thread(
                target=self._speech_worker,
                name="JarvisTTS",
                daemon=True,
            )
            self._worker.start()

    def _speech_worker(self) -> None:
        if not self._tts_enabled:
            return
        try:
            engine = _init_pyttsx3_engine()
            engine.setProperty('rate',   self._rate)
            engine.setProperty('volume', self._volume)
        except Exception as exc:
            print(f"[TTS] Engine init failed: {exc}")
            return

        while True:
            try:
                item = self._q.get()
                if item is _STOP_SENTINEL:
                    break
                
                # Check stop flag before speaking
                if state.is_stop_requested():
                    self._clear_queue()
                    continue

                text, voice_idx = item
                if not text:
                    continue

                # Signal UI update for this segment (if it's a long stream)
                bus.emit("SPEECH_SEGMENT_STARTED", {"text": text})

                self._speaking.set()
                self._done.clear()

                try:
                    vid = self._voices[voice_idx].id
                    engine.setProperty('voice', vid)
                except IndexError:
                    pass
                
                print(f"[Voice] {text}")
                engine.say(text)
                engine.runAndWait()

            except Exception as exc:
                print(f"[TTS] Speech error (ignored): {exc}")
            finally:
                try:
                    self._q.task_done()
                except Exception:
                    pass
                self._speaking.clear()
                if self._q.empty():
                    self._done.set()

    def _clear_queue(self):
        """Empty the queue immediately."""
        try:
            while not self._q.empty():
                self._q.get_nowait()
                self._q.task_done()
        except _queue.Empty:
            pass
        self._done.set()

    def _enqueue(self, text: str, voice_index: int) -> None:
        if text:
            self._done.clear()
            self._q.put((text, voice_index))

    def pre_action(self, intent: str, entity: str = "") -> None:
        pool   = _PRE_ACTION.get(intent, _PRE_ACTION["UNKNOWN"])
        phrase = _pick(pool, entity)
        if phrase:
            if self._neural:
                self._se.speak(phrase, jarvis=False)
            else:
                self._enqueue(phrase, self._female_idx)

    def post_action(self, intent: str, entity: str = "") -> None:
        pool   = _POST_ACTION.get(intent, _POST_ACTION["UNKNOWN"])
        phrase = _pick(pool, entity)
        if phrase:
            if self._neural:
                self._se.speak(phrase, jarvis=True)
            else:
                self._enqueue(phrase, self._jarvis_idx)

    def speak(self, text: str, use_female: bool = False) -> None:
        """Standard speak (synchronous queueing)."""
        if not text:
            return
        if not self._neural and not self._tts_enabled:
            print(f"[Jarvis] {text}")
            return
        if self._neural:
            self._se.speak(text, jarvis=not use_female)
        else:
            idx = self._female_idx if use_female else self._jarvis_idx
            self._enqueue(text, idx)

    def speak_streaming(self, text: str, use_female: bool = False) -> None:
        """
        Split long text into sentences and speak them progressively.
        Jarvis starts speaking the first sentence immediately.
        """
        if not text:
            return
        if not self._neural and not self._tts_enabled:
            print(f"[Jarvis] {text}")
            return
        
        # Split into sentences: matches . ! ? followed by space or end of string
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        for sentence in sentences:
            if sentence.strip():
                if self._neural:
                    self._se.speak(sentence, jarvis=not use_female)
                else:
                    idx = self._female_idx if use_female else self._jarvis_idx
                    self._enqueue(sentence, idx)

    def wait_until_done(self, timeout: float = 15.0) -> None:
        if self._neural and self._se:
            self._se.wait_until_done(timeout=timeout)
        else:
            self._done.wait(timeout=timeout)

    @property
    def is_speaking(self) -> bool:
        if self._neural and self._se:
            return self._se.is_speaking
        return self._speaking.is_set()

    def shutdown(self) -> None:
        if self._neural and self._se:
            self._se.shutdown()
        else:
            self._q.put(_STOP_SENTINEL)
