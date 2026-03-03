"""
response_manager.py  –  Two-voice conversational feedback system
=================================================================
Implements the dual-voice pattern:

  1. FEMALE system voice  →  pre-action announcement
     e.g. "Opening Chrome…"

  2. JARVIS voice  (default) →  post-action confirmation
     e.g. "Chrome has been opened successfully."

Speech runs in a dedicated daemon thread with a queue so:
  • Speech never blocks the main command loop
  • Exceptions inside pyttsx3 never kill Jarvis
  • UI always returns to LISTENING after speaking completes
  • Consecutive speak() calls are queued, never dropped

Public API
----------
    from response_manager import ResponseManager

    rm = ResponseManager()
    rm.pre_action("OPEN_APP", "Chrome")    # female voice
    # … execute command …
    rm.post_action("OPEN_APP", "Chrome")   # jarvis voice
    rm.speak("Custom message.")            # jarvis voice
"""

import pyttsx3
import random
import threading
import queue as _queue

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

    Speech is dispatched through a thread-safe queue so:
      • The main loop never blocks on pyttsx3
      • Exceptions inside TTS are caught and logged (Jarvis never crashes)
      • Every speak() queues a (text, voice_index) pair; the worker thread
        drains the queue sequentially

    Voice assignment
    ----------------
    - voice_index 1  → female system voice (pre-action)
    - voice_index 0  → default/male Jarvis voice (post-action)
    If only one voice is installed, both use index 0.
    """

    def __init__(self, use_neural: bool = True):
        """
        Parameters
        ----------
        use_neural : If True (default) and voice_engine is available,
                     use edge-tts neural voice instead of pyttsx3.
                     Set to False to force the pyttsx3 path.
        """
        self._q       = _queue.Queue()
        self._rate    = 175
        self._volume  = 0.95

        # ── FIX: event that is SET while TTS is playing, CLEAR when idle ──────
        self._speaking = threading.Event()
        self._done     = threading.Event()
        self._done.set()

        # ── Try to delegate to neural SpeechEngine (edge-tts) ─────────────────
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
            # Detect voices before starting thread (avoids race condition)
            _eng = pyttsx3.init()
            self._voices   = _eng.getProperty('voices')
            self._n_voices = len(self._voices)
            del _eng   # discard; worker thread creates its own engine

            self._jarvis_idx = 0
            self._female_idx = 1 if self._n_voices > 1 else 0

            print(f"[ResponseManager] {self._n_voices} pyttsx3 voice(s) found.")
            print(f"  Jarvis voice : {self._voices[self._jarvis_idx].name}")
            if self._n_voices > 1:
                print(f"  System voice : {self._voices[self._female_idx].name}")

            # Start dedicated pyttsx3 speech worker thread
            self._worker = threading.Thread(
                target=self._speech_worker,
                name="JarvisTTS",
                daemon=True,
            )
            self._worker.start()

    # ── Internal speech worker ─────────────────────────────────────────────

    def _speech_worker(self) -> None:
        """
        Runs in a dedicated daemon thread.
        Creates its own pyttsx3 engine so it's never shared across threads.
        Drains the queue indefinitely; never crashes on TTS exceptions.
        """
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
                text, voice_idx = item
                if not text:
                    continue

                # ── FIX: signal that TTS is actively playing ──────────────────
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
                # ── FIX: clear speaking flag; set done if queue now empty ─────
                self._speaking.clear()
                if self._q.empty():
                    self._done.set()

    # ── Private helper ─────────────────────────────────────────────────────

    def _enqueue(self, text: str, voice_index: int) -> None:
        """Push a speech item onto the queue (non-blocking, thread-safe)."""
        if text:
            # Mark as not-done as soon as we enqueue
            self._done.clear()
            self._q.put((text, voice_index))

    # ── Public API ─────────────────────────────────────────────────────────

    def pre_action(self, intent: str, entity: str = "") -> None:
        """
        Speak the pre-action phrase using the FEMALE / assistant voice.
        Call this BEFORE executing the command.
        """
        pool   = _PRE_ACTION.get(intent, _PRE_ACTION["UNKNOWN"])
        phrase = _pick(pool, entity)
        if phrase:
            if self._neural:
                self._se.speak(phrase, jarvis=False)
            else:
                self._enqueue(phrase, self._female_idx)

    def post_action(self, intent: str, entity: str = "") -> None:
        """
        Speak the post-action phrase using the JARVIS / confirmation voice.
        Call this AFTER executing the command.
        """
        pool   = _POST_ACTION.get(intent, _POST_ACTION["UNKNOWN"])
        phrase = _pick(pool, entity)
        if phrase:
            if self._neural:
                self._se.speak(phrase, jarvis=True)
            else:
                self._enqueue(phrase, self._jarvis_idx)

    def speak(self, text: str, use_female: bool = False) -> None:
        """
        General-purpose speak with voice selection.
        Non-blocking: text is queued and spoken asynchronously.
        """
        if not text:
            return
        if self._neural:
            self._se.speak(text, jarvis=not use_female)
        else:
            idx = self._female_idx if use_female else self._jarvis_idx
            self._enqueue(text, idx)

    def set_rate(self, rate: int = 175) -> None:
        """Adjust speech rate. Takes effect on the next utterance."""
        self._rate = rate

    def set_volume(self, volume: float = 0.95) -> None:
        """Adjust volume, 0.0–1.0. Takes effect on the next utterance."""
        self._volume = volume

    def wait_until_done(self, timeout: float = 10.0) -> None:
        """
        Block the calling thread until all queued speech has finished.
        Call this before opening the microphone after a speak() call.
        """
        if self._neural and self._se:
            self._se.wait_until_done(timeout=timeout)
        else:
            self._done.wait(timeout=timeout)

    @property
    def is_speaking(self) -> bool:
        """True while TTS audio is actively playing."""
        if self._neural and self._se:
            return self._se.is_speaking
        return self._speaking.is_set()

    def shutdown(self) -> None:
        """Stop the speech worker thread cleanly."""
        if self._neural and self._se:
            self._se.shutdown()
        else:
            self._q.put(_STOP_SENTINEL)
