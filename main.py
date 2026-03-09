import os
import sys
import threading
import time
from dotenv import load_dotenv

# ============================================
# 1. Load Environment FIRST
# ============================================
env_path = os.path.join(os.path.dirname(__file__), "ni.env")
load_dotenv(dotenv_path=env_path)

# ============================================
# 2. Add root to path
# ============================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================
# Imports
# ============================================
from brain.infra.event_bus import bus
from core.config import config
from core.monitor import activity_logger
from core.audio.voice_control import take_command
from core.audio.voice_utils import set_response_manager
from ui.visual_ui import JarvisUI

# Initialize orchestrator
from brain.infra.database import init_db


class JarvisApp:

    def __init__(self):

        # Initialize DB
        init_db()
        # Initialize orchestrator after DB setup (it starts reminder threads)
        from brain.orchestrator import orchestrator as _orchestrator
        self.orchestrator = _orchestrator

        config.validate_config()

        self.running = True
        self.ui = None

        # Route utility speech calls through orchestrator's voice manager.
        set_response_manager(self.orchestrator.rm)

        # Event subscriptions
        bus.subscribe("SPEECH_REQUESTED", self.handle_speech)
        bus.subscribe("SYSTEM_EXIT", self.shutdown)

    # =====================================================
    # Handle speech event
    # =====================================================
    def handle_speech(self, data: dict):
        """Handle SPEECH_REQUESTED event — UI updates only, NO speaking here.
        The orchestrator already calls rm.speak() directly after emitting this event.
        This handler only updates the UI state and subtitle text.
        """
        if not data:
            return

        text = data.get("text")
        ui_state = data.get("ui_state", "SPEAKING")

        # Update UI state
        if self.ui:
            self.ui.set_state(ui_state)

        # Update subtitle (display only — no TTS here)
        if text and self.ui:
            self.ui.set_subtitle(text)

        # Log to console
        if text:
            print(f"[Jarvis] {text}")

        # Return UI to listening state (brief delay handled by voice_loop)
        if self.ui:
            self.ui.set_state("LISTENING")

    # =====================================================
    # Voice Loop
    # =====================================================
    def voice_loop(self):

        # Wait for UI
        while self.ui is None and self.running:
            time.sleep(0.1)

        print("[Voice] JARVIS Listening...")

        while self.running:

            try:

                if self.ui:
                    self.ui.set_state("LISTENING")

                query = take_command(ui=self.ui)

                if not query:
                    time.sleep(0.1)
                    continue

                query = query.strip()

                if query:

                    print(f"[Voice] Captured: {query}")

                    if self.ui:
                        self.ui.set_state("THINKING")
                        self.ui.set_subtitle("Processing...")

                    bus.emit(
                        "QUERY_RECEIVED",
                        {
                            "query": query,
                            "ui": self.ui
                        }
                    )

                time.sleep(0.1)

            except Exception as e:

                print(f"[VoiceLoop Error] {e}")

                if self.ui:
                    self.ui.set_state("IDLE")

                time.sleep(1)

    # =====================================================
    # Shutdown
    # =====================================================
    def shutdown(self, _=None):

        self.running = False

        print("\n[System] JARVIS shutting down...")

        try:
            bus.emit("FORCE_STOP", {})
        except:
            pass

        os._exit(0)

    # =====================================================
    # Run Application
    # =====================================================
    def run(self):

        # Start background logger
        activity_logger.start_logger()

        # Start voice thread
        # Initialize UI FIRST
        self.ui = JarvisUI()

        # Start voice thread
        self.voice_thread = threading.Thread(
            target=self.voice_loop,
            name="VoiceLoop",
            daemon=True
        )

        self.voice_thread.start()

        print("=" * 40)
        print("  JARVIS PRODUCTION SPINE : ONLINE")
        print("=" * 40)

        # Startup greeting
        bus.emit("STARTUP_GREETING", {})

        # Run UI (fallback to console mode if GUI is unavailable)
        try:
            self.ui.run()
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"[UI] GUI unavailable, running in console mode: {e}")
            while self.running:
                time.sleep(0.5)


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":

    app = JarvisApp()
    app.run()
