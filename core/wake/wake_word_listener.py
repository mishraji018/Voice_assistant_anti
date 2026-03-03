"""
wake_word_listener.py  –  Continuous "Hey Jarvis" wake-word listener
=====================================================================
Listens for wake word in foreground or background daemon thread.

Public API
----------
    ww = WakeWordListener(speak_fn=rm.speak, ui=ui)
    ww.start_background()           # start daemon thread (works minimized)
    ww.wait_for_wake()              # block until wake word heard
    ww.start_active_timer(30)       # start inactivity countdown
    ww.beat()                       # reset timer after each command
    ww.is_timed_out()               # True if idle too long
    ww.go_idle()                    # force return to idle
"""

import time
import threading
import speech_recognition as sr

# ── Wake word variants ────────────────────────────────────────────────────────
WAKE_WORDS = [
    "hey jarvis", "jarvis", "hi jarvis", "hello jarvis",
    "ok jarvis", "okay jarvis",
    # Hinglish
    "jarvis sun", "jarvis suno", "sun jarvis",
]

# ── Tuning ────────────────────────────────────────────────────────────────────
_PHRASE_LIMIT  = 4.0    # max seconds per listen clip
_WAIT_TIMEOUT  = 3.0    # give up clip after this many seconds silence
_COOLDOWN      = 2.5    # ignore re-fires within this window


class WakeWordListener:

    def __init__(self, speak_fn, ui=None):
        self.speak = speak_fn
        self.ui    = ui

        self.rec = sr.Recognizer()
        self.rec.pause_threshold            = 0.6
        self.rec.energy_threshold           = 300
        self.rec.dynamic_energy_threshold   = True

        # Active-session timer
        self._active_since   = None       # float (monotonic) or None
        self._active_timeout = 30.0
        self._timer_lock     = threading.Lock()

        # Duplicate-trigger guard
        self._last_wake = 0.0

        # Background thread state
        self._wake_event = threading.Event()
        self._bg_running = False

    # ── Low-level listen ──────────────────────────────────────────────────────

    def _listen_once(self) -> str:
        """Record one short clip and return lowercase transcript (or '')."""
        try:
            with sr.Microphone() as source:
                self.rec.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.rec.listen(
                    source,
                    timeout=_WAIT_TIMEOUT,
                    phrase_time_limit=_PHRASE_LIMIT,
                )
            return self.rec.recognize_google(audio, language="en-IN").lower().strip()
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            time.sleep(2)
            return ""
        except Exception as exc:
            print(f"[WakeWord] Error: {exc}")
            return ""

    def _is_wake(self, text: str) -> bool:
        return any(w in text for w in WAKE_WORDS)

    def _cooldown_ok(self) -> bool:
        return (time.monotonic() - self._last_wake) >= _COOLDOWN

    def _ui_set_state(self, state: str) -> None:
        """Thread-safe UI state update."""
        if not self.ui:
            return
        try:
            root = getattr(self.ui, "_root", None) or getattr(self.ui, "root", None)
            if root:
                root.after(0, lambda s=state: self.ui.set_state(s))
            else:
                self.ui.set_state(state)
        except Exception:
            pass

    def _on_wake(self) -> None:
        self._last_wake = time.monotonic()
        print("[Jarvis] 🟢 Wake word detected!")
        # ── FIX 1: Pre-emptively mark session active HERE, before wait_for_wake()
        # returns. This closes the race window where the bg thread would grab the
        # mic again between wake detection and start_active_timer() being called.
        with self._timer_lock:
            self._active_since = time.monotonic()
        self._ui_set_state("WAKE")

    # ── Public: wait for wake ─────────────────────────────────────────────────

    def wait_for_wake(self) -> None:
        """
        Block until a wake word is heard.
        In background mode: just waits on the threading.Event set by the daemon.
        In foreground mode: listens directly on this thread.
        """
        if self._bg_running:
            print("\n[Jarvis] 💤 Idle — background listener active…")
            self._ui_set_state("IDLE")
            self._wake_event.wait()   # woken by daemon thread
            self._wake_event.clear()
            return

        # ── Foreground mode ───────────────────────────────────────────────
        print("\n[Jarvis] Idle — waiting for wake word…")
        self._ui_set_state("IDLE")

        while True:
            text = self._listen_once()
            if not text:
                continue
            print(f"[WakeWord] Heard: '{text}'")
            if self._is_wake(text) and self._cooldown_ok():
                self._on_wake()
                return

    # ── Background daemon thread ──────────────────────────────────────────────

    def start_background(self) -> None:
        """
        Start a daemon thread that listens continuously.
        Wake word detection works even when the window is minimized or unfocused.
        Safe to call multiple times (no-op after first call).
        """
        if self._bg_running:
            return
        self._bg_running = True
        t = threading.Thread(target=self._bg_loop, name="WakeWordBG", daemon=True)
        t.start()
        print("[WakeWord] Background listener thread started.")

    def _bg_loop(self) -> None:
        """Daemon thread: listens and fires wake_event when phrase is heard."""
        while self._bg_running:
            # ── FIX 2: Check active_since under the lock (matches _on_wake's write)
            with self._timer_lock:
                is_active = self._active_since is not None
            if is_active:
                time.sleep(0.1)   # back off cheaply while command session runs
                continue

            text = self._listen_once()
            if text:
                print(f"[WakeWord-BG] Heard: '{text}'")
            if text and self._is_wake(text) and self._cooldown_ok():
                # _on_wake() sets _active_since BEFORE we release the event,
                # so the main thread sees the flag set as soon as it unblocks.
                self._on_wake()
                self._wake_event.set()   # unblock wait_for_wake()
                # Stop the inner loop immediately — mic now belongs to main thread
                break

    # ── Active-session timer ──────────────────────────────────────────────────

    def start_active_timer(self, timeout_seconds: float = 30.0) -> None:
        """Start (or restart) the inactivity countdown."""
        with self._timer_lock:
            self._active_since   = time.monotonic()
            self._active_timeout = timeout_seconds

    def beat(self) -> None:
        """Reset inactivity timer — call after each successful command."""
        self.start_active_timer(self._active_timeout)

    def is_timed_out(self) -> bool:
        """Return True if silently idle longer than timeout."""
        with self._timer_lock:
            if self._active_since is None:
                return False
            return (time.monotonic() - self._active_since) >= self._active_timeout

    def go_idle(self) -> None:
        """Force a return to idle state (timeout fired or session ended)."""
        with self._timer_lock:
            self._active_since = None
            self._last_wake    = 0.0   # allow an immediate fresh wake
        print("[Jarvis] ⏸  Returning to idle.")
        self.speak("Going to sleep. Say Hey Jarvis to wake me up.")
        self._ui_set_state("IDLE")
        # ── FIX 3: Restart a fresh bg listener thread.
        # The previous _bg_loop broke out of its loop on wake; we need a new
        # thread so wake-word detection resumes cleanly without holding any
        # stale mic state from the previous session.
        self._bg_running = False          # signal old thread (already exited) done
        self._wake_event.clear()          # reset event for next cycle
        self._bg_running = True
        t = threading.Thread(target=self._bg_loop, name="WakeWordBG", daemon=True)
        t.start()
        print("[WakeWord] Background listener restarted.")