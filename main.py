
import os
import sys
import threading
import time
from dotenv import load_dotenv

# 1. Load Environment FIRST
env_path = os.path.join(os.path.dirname(__file__), "ni.env")
load_dotenv(dotenv_path=env_path)

# 2. Add root to path for brain imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 3. Imports after env load
from brain.infra.event_bus import bus
from core.config import config
from core.monitor import activity_logger
from core.audio.voice_control import take_command
from ui.visual_ui import JarvisUI

# Initialize Orchestrator to register event handlers
# Import here ensures orchestrator starts before anything else
from brain.orchestrator import orchestrator
from brain.infra.database import init_db

class JarvisApp:
    def __init__(self):
        # 0. Initialize Database FIRST
        init_db()
        config.validate_config()
        self.running = True
        self.ui = None # Initialize as None
        
        # Subscribe to events
        bus.subscribe("SPEECH_REQUESTED", self.handle_ui_feedback)
        bus.subscribe("SYSTEM_EXIT", self.shutdown)

    def handle_ui_feedback(self, data: dict):
        """Update UI based on speech events."""
        if self.ui:
            if data.get("ui_state"):
                self.ui.set_state(data.get("ui_state"))
            if data.get("text"):
                # Ensure speech feedback updates subtitle or log context
                self.ui.set_subtitle(data.get("text"))

    def voice_loop(self):
        """Thread-safe voice recognition loop."""
        # WAIT for UI to be initialized by main thread
        while self.ui is None and self.running:
            time.sleep(0.1)
            
        print("[Voice] JARVIS Listening...")
        while self.running:
            # Query is captured here
            query = take_command(ui=self.ui)
            if query and query.strip():
                # [FIX]: UI transcript box must show user's spoken text IMMEDIATELY
                if self.ui:
                    self.ui.set_subtitle(f"You said: {query}")
                
                print(f"[Voice] Captured: {query}")
                # Emit to Event Bus -> Orchestrator processes it
                bus.emit("QUERY_RECEIVED", {"query": query, "ui": self.ui})
            
            time.sleep(0.1)

    def shutdown(self, _=None):
        """Graceful shutdown of all threads."""
        self.running = False
        print("\n[System] JARVIS shutting down...")
        bus.emit("FORCE_STOP", {})
        sys.exit(0)

    def run(self):
        """Main entry point."""
        # 1. Start Activity Logger (Background Task)
        # This will call cleanup_old_activity which now has tables
        activity_logger.start_logger()
        
        # 2. Start Voice Thread (Sensor Task)
        # It will wait for self.ui to be set before proceeding
        self.voice_thread = threading.Thread(
            target=self.voice_loop, 
            name="VoiceLoop",
            daemon=True
        )
        self.voice_thread.start()
        
        print("="*40)
        print("  JARVIS PRODUCTION SPINE : ONLINE  ")
        print("="*40)
        
        # 3. Initialize UI (Happens on main thread)
        self.ui = JarvisUI()
        
        # 4. Trigger Startup Greeting (Async)
        bus.emit("STARTUP_GREETING", {})
        
        # 5. Start UI Mainloop (BLOCKING)
        try:
            self.ui.run()
        except KeyboardInterrupt:
            self.shutdown()

if __name__ == "__main__":
    app = JarvisApp()
    app.run()


