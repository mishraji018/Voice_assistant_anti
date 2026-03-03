
import os
import sys
import threading
from typing import Dict, Any

from brain.infra.event_bus import bus
from brain.intents import detect_intent
from brain.learning import get_correction, save_correction
from brain.knowledge.engine import get_answer
from brain.knowledge import weather
from core.infra.translator import translate_to_english
from brain.infra.database import log_activity
from core.runtime.response_manager import ResponseManager
from commands.system import command_system

class Orchestrator:
    """
    JARVIS Orchestrator: The brain of the application.
    Wires Intent -> Command -> Feedback -> Memory.
    """
    def __init__(self):
        self.rm = ResponseManager()
        # Subscribe to query events from voice loop
        bus.subscribe("QUERY_RECEIVED", self.process_query)
        bus.subscribe("STARTUP_GREETING", self.startup_greeting)
        bus.subscribe("SYSTEM_EXIT", self.handle_stop)

    def startup_greeting(self, _=None):
        """Initial startup greeting (Hindi Female Voice)."""
        response = "Hi, I am Jarvis. Kya madad kar sakti hoon aapki?"
        bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
        self.rm.speak(response, use_female=True)

    def process_query(self, data: Dict[str, Any]):
        """
        Main execution pipeline:
        Translation -> Intent Detection -> Execution -> Feedback
        """
        text = data.get("query", "")
        ui = data.get("ui")
        
        if not text:
            return

        print(f"[Brain] Processing: {text}")
        if ui: ui.set_subtitle(f"Thinking...")

        # 1. Personality / "Who are you?" Special Case
        if "who are you" in text.lower() or "kaun ho" in text.lower():
            response = "I am Jarvis, your smart Hindi-English personal assistant. Main apki help ke liye hamesha taiyar hoon, sir."
            bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
            self.rm.speak(response, use_female=True)
            return

        # 2. Check Learning Corrections
        correction = get_correction(text)
        if correction:
            print(f"[Brain] Using learned correction: {correction}")
            text = correction # Use the corrected phrase

        # 3. Translate / Normalize
        english_text = translate_to_english(text, "auto")
        
        # 4. Detect Intent
        result = detect_intent(english_text)
        intent = result["intent"]
        entity = result["entity"]
        
        print(f"[Brain] Intent: {intent} | Entity: {entity}")

        # 5. Pre-Action Feedback
        self.rm.pre_action(intent, entity)

        # 6. Command Routing & Execution
        response_text = None
        
        # Check if user is correcting us (Simple pattern)
        if "no" in text.lower() and "actually" in text.lower():
            response_text = "Mera maafi chahungi, sir. I will remember that next time."
            save_correction("previous_command", "correct_command")

        elif intent == "WEATHER":
            # Direct Weather Handler
            response_text = weather.handle_weather_query(text)
            log_activity("WEATHER_QUERY", entity or "Current Location")

        elif intent == "OPEN_APP" or intent == "SYSTEM_CONTROL":
            response_text = command_system.run(english_text)
            
        elif intent == "INFO_QUERY":
            # Knowledge Engine (Wiki + Ollama)
            response_text = get_answer(english_text)
            
        elif intent == "SMALL_TALK":
            response_text = "Always a pleasure to help, sir."
        
        # 7. Post-Action Feedback
        if response_text:
            if response_text.startswith("SYSTEM_ACTION:"):
                action = response_text.split(":")[1]
                command_system.execute_pc_action(action)
            else:
                # Emit event first so UI shows text while/before speaking
                bus.emit("SPEECH_REQUESTED", {"text": response_text, "ui_state": "SPEAKING"})
                # Only use rm confirmation pool if NOT already custom handled (like weather)
                if intent != "WEATHER" and intent != "SMALL_TALK":
                    self.rm.post_action(intent, entity)
                self.rm.speak(response_text)
        else:
            # AI Fallback for anything else
            response_text = get_answer(english_text)
            bus.emit("SPEECH_REQUESTED", {"text": response_text, "ui_state": "SPEAKING"})
            self.rm.speak(response_text)

        if ui: ui.set_state("IDLE")



    def handle_stop(self, _):
        """Clean shutdown."""
        self.rm.shutdown()

# Managed orchestrator instance
orchestrator = Orchestrator()
