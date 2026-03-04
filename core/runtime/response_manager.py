
import pyttsx3
import random
import threading
import queue as _queue
import re
from brain.infra.event_bus import bus
from core.state.runtime_state import state

# ── Optional: neural voice engine (edge-tts + pygame) ─────────────────────
try:
    from voice_engine import SpeechEngine as _SpeechEngine
    _NEURAL_AVAILABLE = True
except Exception:
    _NEURAL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Phrase pools
# ---------------------------------------------------------------------------

_PRE_ACTION: dict[str, list[str]] = {
    "OPEN_APP"       : ["Opening {entity}…",
                        "Launching {entity}, please wait…",
                        "Starting {entity} for you…",
                        "One moment — bringing up {entity}…"],

    "CLOSE_WINDOW"   : ["Closing the window…",
                        "Shutting it down…",
                        "Closing that for you…"],

    "SEARCH_WEB"     : ["Searching for {entity} on the web…",
                        "Looking up {entity}…",
                        "Googling {entity} right now…"],

    "SYSTEM_CONTROL" : ["Executing system command…",
                        "Applying your system settings…",
                        "Processing that request…"],

    "MEDIA_CONTROL"  : ["Playing your media…",
                        "Starting playback…",
                        "Loading your content…"],

    "INFO_QUERY"     : ["Fetching the information…",
                        "Let me check that…",
                        "Looking that up for you…"],

    "NOTE_TASK"      : ["Saving your note…",
                        "Setting that reminder…",
                        "Adding to your list…"],

    "CALCULATOR"     : ["Calculating…",
                        "Running the numbers…"],

    "NEWS"           : ["Fetching the latest news…",
                        "Loading your headlines…"],

    "SMALL_TALK"     : [],   # no pre-action for small talk

    "UNKNOWN"        : ["Processing your request…",
                        "Let me try that…"],
}

_POST_ACTION: dict[str, list[str]] = {
    "OPEN_APP"       : ["{entity} has been opened successfully.",
                        "{entity} is now running.",
                        "Done! {entity} is open and ready.",
                        "I've launched {entity} for you."],

    "CLOSE_WINDOW"   : ["Window closed successfully.",
                        "Done, it's all closed up.",
                        "I've closed that for you."],

    "SEARCH_WEB"     : ["Search results for {entity} are ready.",
                        "I've opened the results for {entity}.",
                        "Done! Take a look at the results."],

    "SYSTEM_CONTROL" : ["System command executed successfully.",
                        "Done — your system has been updated.",
                        "All set on the system side."],

    "MEDIA_CONTROL"  : ["Media is now playing. Enjoy!",
                        "Done! Hope you enjoy it.",
                        "Playback started."],

    "INFO_QUERY"     : ["Hope that answers your question!",
                        "There you go.",
                        "That's what I found for you."],

    "NOTE_TASK"      : ["Got it — all saved.",
                        "Reminder set successfully.",
                        "Your task has been noted."],

    "CALCULATOR"     : ["There's your result.",
                        "Calculation complete!"],

    "NEWS"           : ["That's the latest news. Stay informed!",
                        "Here are your top stories."],

    "SMALL_TALK"     : ["Always a pleasure chatting with you!",
                        "Good to talk! How else can I help?"],

    "UNKNOWN"        : ["I did my best with that.",
                        "Let me know if you need anything else."],
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
            _eng = pyttsx3.init()
            self._voices   = _eng.getProperty('voices')
            self._n_voices = len(self._voices)
            del _eng

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
        try:
            engine = pyttsx3.init()
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
