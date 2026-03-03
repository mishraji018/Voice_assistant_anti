"""
threaded_wake_loop.py  –  Integration snippet: faster wake + performance safeguards
====================================================================================
Drop-in replacement for the run_jarvis() main loop section in main.py.

What this adds
--------------
  1. WAKE LISTENER THREAD  – a dedicated background thread owns the microphone
     exclusively during idle.  main.py's command loop never touches the mic
     at the same time.
  2. COMMAND QUEUE         – wake thread posts a signal; command thread picks
     it up immediately, cutting latency.
  3. IDLE CPU GUARD        – the command thread sleeps long when nothing is
     happening, preventing a busy-spin.
  4. MIC RELEASE PROTOCOL  – the wake thread closes the mic before the command
     thread opens its own sr.Microphone() context.
  5. GRACEFUL ERROR HANDLING – every listen / recognise call is wrapped so a
     network outage or audio glitch never crashes the whole assistant.

How to plug in
--------------
  Option A (minimal):
      Replace the while-True block in run_jarvis() with the code labelled
      "── Slot this into run_jarvis() ──" at the bottom of this file.

  Option B (standalone test):
      python threaded_wake_loop.py
"""

import queue
import threading
import time
import speech_recognition as sr

# ── tunables ──────────────────────────────────────────────────────────────────
WAKE_PHRASE_LIMIT  = 3.0    # seconds to capture each wake-word snippet
WAKE_TIMEOUT       = 3.0    # listen() timeout during idle (sec)
COMMAND_TIMEOUT    = 5.0    # listen() timeout during active session (sec)
IDLE_POLL_INTERVAL = 0.05   # seconds to sleep when nothing pending
MIC_HANDOFF_DELAY  = 0.15   # brief pause after wake thread releases mic


# ─────────────────────────────────────────────────────────────────────────────
# Wake-word thread (runs permanently in background)
# ─────────────────────────────────────────────────────────────────────────────

WAKE_PHRASES = {
    "hey jarvis", "jarvis", "aye jarvis", "hi jarvis",
    "ok jarvis", "okay jarvis", "hello jarvis",
    "jarvis sun", "jarvis suno",
}

class _WakeThread(threading.Thread):
    """
    Dedicated thread that polls the microphone for the wake word.
    Posts a sentinel on `wake_queue` when detected.
    Pauses itself while `active_event` is set (command session in progress).
    """

    def __init__(self, wake_queue: queue.Queue, active_event: threading.Event):
        super().__init__(name="WakeWordThread", daemon=True)
        self._q       = wake_queue
        self._active  = active_event
        self._stop    = threading.Event()
        self._rec     = sr.Recognizer()
        self._rec.pause_threshold  = 0.6
        self._rec.energy_threshold = 300

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            # Yield mic to command thread while session is active
            if self._active.is_set():
                time.sleep(IDLE_POLL_INTERVAL)
                continue

            text = self._listen_once()
            if self._is_wake(text):
                self._q.put("WAKE")   # signal main loop
            time.sleep(IDLE_POLL_INTERVAL)

    def _listen_once(self) -> str:
        try:
            with sr.Microphone() as mic:
                self._rec.adjust_for_ambient_noise(mic, duration=0.2)
                audio = self._rec.listen(
                    mic,
                    timeout=WAKE_TIMEOUT,
                    phrase_time_limit=WAKE_PHRASE_LIMIT,
                )
            return self._rec.recognize_google(audio, language="en-IN").lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except sr.RequestError:
            time.sleep(1)
            return ""
        except OSError:
            # Mic in use by command thread — back off briefly
            time.sleep(MIC_HANDOFF_DELAY)
            return ""

    @staticmethod
    def _is_wake(text: str) -> bool:
        return any(p in text for p in WAKE_PHRASES)


# ─────────────────────────────────────────────────────────────────────────────
# Single-shot command listen (called from main loop thread only)
# ─────────────────────────────────────────────────────────────────────────────

def _listen_for_command() -> dict:
    """
    One listen attempt during an active session.
    Returns {"raw": str, "lang": str}.  Empty string on any failure.
    """
    rec = sr.Recognizer()
    rec.pause_threshold = 0.8
    try:
        with sr.Microphone() as mic:
            rec.adjust_for_ambient_noise(mic, duration=0.2)
            audio = rec.listen(mic, timeout=COMMAND_TIMEOUT, phrase_time_limit=10)
        text = rec.recognize_google(audio, language="en-IN")
        return {"raw": text, "lang": "en-IN"}
    except sr.WaitTimeoutError:
        return {"raw": "", "lang": "en-IN"}
    except sr.UnknownValueError:
        return {"raw": "", "lang": "en-IN"}
    except sr.RequestError as e:
        print(f"[Listen] API error: {e}")
        return {"raw": "", "lang": "en-IN"}
    except OSError as e:
        print(f"[Listen] Mic error: {e}")
        return {"raw": "", "lang": "en-IN"}


# ─────────────────────────────────────────────────────────────────────────────
# ── Slot this into run_jarvis() ──
#
#   Replace your current while-True loop in main.py with this block.
#   Prerequisite imports already present in main.py are omitted here.
# ─────────────────────────────────────────────────────────────────────────────
_INTEGRATION_SNIPPET = '''
# ── Threaded wake loop (add near top of run_jarvis) ──────────────────────────
import queue as _queue
import threading as _threading

# Replace: ww = WakeWordListener(...)
# With the following two objects:
_wake_queue  = _queue.Queue(maxsize=1)
_active_flag = _threading.Event()          # SET during command session

from core.wake.threaded_wake_loop import _WakeThread, _listen_for_command

_wake_thread = _WakeThread(_wake_queue, _active_flag)
_wake_thread.start()

# ── OUTER LOOP ────────────────────────────────────────────────────────────────
while True:
    ui.set_state("IDLE")
    print("\\n[Jarvis] Waiting for wake word…")

    # Block (cheaply) until wake thread posts a signal
    _wake_queue.get()                    # ← replaces ww.wait_for_wake()
    _active_flag.set()                   # block wake thread from mic
    time.sleep(0.15)                     # mic handoff pause
    memory.clear_session()
    rm.speak(random.choice(WAKE_CONFIRMATIONS))

    active_deadline = time.monotonic() + ACTIVE_TIMEOUT

    # ── INNER LOOP ───────────────────────────────────────────────────────────
    while True:
        if time.monotonic() > active_deadline:
            rm.speak("Going to sleep. Say hey Jarvis to wake me up.")
            break

        ui.set_state("LISTENING")
        result   = _listen_for_command()   # ← replaces listen()
        raw_text = result["raw"]
        lang     = result["lang"]

        if not raw_text:
            time.sleep(IDLE_POLL_INTERVAL)
            continue

        active_deadline = time.monotonic() + ACTIVE_TIMEOUT  # reset on every heard phrase

        # ── rest of your existing inner loop (translate, route, execute) ────
        # (unchanged — paste your existing lines here)

    _active_flag.clear()    # release mic back to wake thread
    ui.set_state("IDLE")
'''


# ─────────────────────────────────────────────────────────────────────────────
# Quick standalone demo
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Threaded wake-word demo. Say 'Hey Jarvis'…")
    wq = queue.Queue(maxsize=1)
    ae = threading.Event()
    wt = _WakeThread(wq, ae)
    wt.start()

    while True:
        wq.get()
        print("[Demo] Wake word! Now listening for command…")
        ae.set()
        time.sleep(0.15)
        result = _listen_for_command()
        print(f"[Demo] You said: '{result['raw']}'")
        ae.clear()
        print("[Demo] Back to sleep.")
