
import os
import sys
import threading
from typing import Dict, Any

from brain.infra.event_bus import bus
from brain.intents import detect_intent
from brain.learning import (
    get_correction,
    save_correction,
    get_learned_intent,
    save_learned_intent,
)
from brain.knowledge.engine import get_answer
from brain.knowledge import weather, nutrition
from brain.health import wellness_tracker
from brain import capabilities
from brain.vision import screen_analyzer
from brain.agent.task_agent import task_agent
from brain.memory import long_term_memory
from brain.agent import browser_agent
from brain.productivity.task_manager import TaskManager
from core.infra.translator import translate_to_english
from brain.infra.database import log_activity
from core.runtime.response_manager import ResponseManager
from core.state.runtime_state import state
from brain.memory.conversation_memory import memory
from commands.system import command_system

# ── Stop words (matched as substrings) ────────────────────────────────────────
STOP_WORDS = ["stop", "ruko", "bas", "cancel", "band karo"]

# ── Wake words ────────────────────────────────────────────────────────────────
WAKE_PHRASES = ["hey jarvis", "hello jarvis", "hi jarvis", "ok jarvis", "okay jarvis"]
WAKE_EXACT = ["jarvis"]


def _contains_any(text: str, phrases: list) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def _is_wake_only(text: str) -> bool:
    cleaned = text.strip().lower()
    if cleaned in WAKE_EXACT: return True
    for phrase in WAKE_PHRASES:
        if cleaned == phrase: return True
        if cleaned.startswith(phrase):
            remainder = cleaned[len(phrase):].strip()
            if not remainder or remainder in ["", ".", "?", "!"]: return True
    return False


class Orchestrator:
    """
    JARVIS Orchestrator: The brain of the application.
    Now with Memory, Streaming Speech, and Local Intent Optimization.
    """
    def __init__(self):
        self.rm = ResponseManager()
        self._current_ui = None
        
        # Subscribe to events
        bus.subscribe("QUERY_RECEIVED", self.process_query)
        bus.subscribe("STARTUP_GREETING", self.startup_greeting)
        bus.subscribe("SYSTEM_EXIT", self.handle_stop)
        
        # Initialize Task Manager
        self.task_manager = TaskManager(self.rm)
        self.task_manager.start_reminder_checker()
        bus.subscribe("SPEECH_SEGMENT_STARTED", self.handle_speech_segment)

    def startup_greeting(self, _=None):
        response = "Hi, I am Jarvis. Kya madad kar sakti hoon aapki?"
        bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
        self.rm.speak(response, use_female=True)

    def handle_speech_segment(self, data: Dict[str, Any]):
        """Update UI subtitle as each sentence is spoken."""
        text = data.get("text", "")
        if self._current_ui and text:
            # Update message box with the current sentence for progressive visual
            self._current_ui.set_message(text, "#00e5ff")

    def process_query(self, data: Dict[str, Any]):
        text = data.get("query", "")
        ui = data.get("ui")
        self._current_ui = ui
        
        if not text: return

        # ── 0. STOP check ─────────────────────────────────────────────────────
        if _contains_any(text, STOP_WORDS):
            state.request_stop()
            bus.emit("FORCE_STOP", {}) 
            response = "Sir kya hua? Kuch aur search karna hai aapko? Main yahi hoon."
            if ui:
                ui.set_message(response, "#ffab40")
                ui.set_subtitle("")
            bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
            self.rm.speak(response, use_female=True)
            state.clear_stop()
            if ui:
                ui.set_state("IDLE")
                ui.clear_message()
            return

        # ── 0b. Wake check ────────────────────────────────────────────────────
        if _is_wake_only(text):
            response = "Sir main yahi hoon, aapke paas. Bas order dijiye mujhe kya karna hoga."
            if ui: ui.set_message(response, "#00e5ff")
            bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
            self.rm.speak(response, use_female=True)
            if ui: ui.set_state("IDLE")
            return

        # Strip wake prefix
        cleaned_text = text.strip().lower()
        for phrase in WAKE_PHRASES + WAKE_EXACT:
            if cleaned_text.startswith(phrase):
                cleaned_text = cleaned_text[len(phrase):].strip()
                break
        if cleaned_text: text = cleaned_text

        state.clear_stop()
        if ui:
            ui.set_state("THINKING")
            ui.set_subtitle("Thinking...")

        # ── 1. Get History Context ────────────────────────────────────────────
        history = memory.get_history_string()

        # 2. Translate / Intent Detection
        english_text = translate_to_english(text, "auto")
        
        # ── 2b. Intent Learning & Correction Loop ─────────────────────────────
        learned_intent = get_learned_intent(english_text)
        
        # Check for correction: "No, I meant [Intent]"
        if any(c in english_text for c in ["no i meant", "nahi main", "instead", "use"]):
            if state.last_query:
                # We try to extract the intent from the correction or context
                # For simplicity, if it matches a known intent keyword
                for known_intent in ["WEATHER", "OPEN_APP", "WELLNESS_TRACKING", "NOTEPAD_WRITE"]:
                     if known_intent.lower().replace("_", " ") in english_text:
                         save_learned_intent(state.last_query, known_intent)
                         self.rm.speak(f"Sir, maine seekh liya hai. Agli baar se '{state.last_query}' bypass ho jayega.", use_female=True)
                         return

        result = detect_intent(english_text)
        intent = learned_intent if learned_intent else result["intent"]
        entity = result["entity"]
        
        # Save for learning next turn
        state.last_query = english_text
        state.last_intent = intent
        
        print(f"[Brain] Intent: {intent} (Learned: {bool(learned_intent)}) | Entity: {entity}")

        # ── 3. Local Intent Fast-Path ─────────────────────────────────────────
        response_text = None
        
        if intent == "WEATHER":
            response_text = weather.handle_weather_query(text)
        elif intent == "NUTRITION_QUERY":
            response_text = nutrition.handle_nutrition_query(text)
        elif intent == "WELLNESS_TRACKING":
            response_text = wellness_tracker.handle_wellness_query(text)
        elif intent == "CAPABILITY_QUERY":
            response_text = capabilities.get_capability_response(english_text)
        elif intent == "NOTEPAD_WRITE":
            response_text = command_system.write_to_notepad(entity)
        elif intent == "MEMORY_STORE" or intent == "MEMORY_QUERY":
            response_text = long_term_memory.lt_memory.process_query(text)
        elif intent == "BROWSER_SEARCH":
            if ui: ui.set_subtitle("Searching Web...")
            response_text = browser_agent.browser_agent.search_and_summarize(entity if entity else english_text)
        elif intent == "TASK_CREATE" or intent == "TASK_LIST":
            response_text = self.task_manager.handle_query(text)
        elif intent == "VISION_QUERY":
            if ui: ui.set_subtitle("Analyzing Screen...")
            response_text = screen_analyzer.analyze_screen()
        elif intent == "COMPLEX_QUERY":
            if ui: ui.set_subtitle("Thinking (Agent)...")
            # The agent can call a progress callback
            response_text = task_agent.execute_plan(english_text, callback=lambda msg: ui.set_subtitle(msg) if ui else None)
        elif intent in ["OPEN_APP", "SYSTEM_CONTROL", "CLOSE_WINDOW", "MEDIA_CONTROL"]:
            response_text = command_system.run(english_text)
        elif intent == "SMALL_TALK":
            # ── 0c. Daily Wellness Check-in ──────────────────────────────────────
            # Trigger ONLY during small talk and ONLY once a day
            import datetime
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            if state.last_checkin_dt != today_str:
                state.last_checkin_dt = today_str
                checkin_msg = "Good morning sir! Aaj aapne apna wellness routine start kiya? Pani kitna piya hai abhi tak? Aur sir, kya aapne aaj exercise ki ya kal raat ki neend kaise rahi?"
                self.rm.speak(checkin_msg, use_female=True)
            
            response_text = "Always a pleasure to help, sir."
            if "who are you" in text.lower() or "kaun ho" in text.lower():
                response_text = "I am Jarvis, your smart Hindi-English personal assistant. Main apki help ke liye hamesha taiyar hoon, sir."
        
        # ── 4. Knowledge Engine Fallback (for INFO_QUERY or UNKNOWN) ──────────
        if not response_text and not state.is_stop_requested():
            if ui: ui.set_subtitle("Searching...")
            self.rm.speak("Thoda sabar kijiye sir, main laa rahi hoon...", use_female=True)
            # Pass conversation history for pronoun resolution
            response_text = get_answer(english_text, history=history)

        # ── 5. finalize and Save Turn ─────────────────────────────────────────
        if response_text and not state.is_stop_requested():
            # Save to memory for follow-up
            memory.add_turn(text, response_text)
            
            # Emit event first so UI shows text
            bus.emit("SPEECH_REQUESTED", {"text": response_text, "ui_state": "SPEAKING"})
            
            # Use STREAMING speech for long responses
            if len(response_text) > 60:
                self.rm.speak_streaming(response_text)
            else:
                self.rm.speak(response_text)

        # ── 8. Occasional Wellness Reminder ──────────────────────────────────
        import random
        if random.random() < 0.15: # 15% chance
            reminder = random.choice([
                "Sir, thoda pani peelijiye, hydration zaroori hai.",
                "Sir, thoda break lekar walk kar lijiye, it's good for health.",
                "Sir, neend achhi lijiye aaj raat, recovery ke liye important hai."
            ])
            self.rm.speak(reminder, use_female=True)

        if ui: ui.set_state("IDLE")

    def handle_stop(self, _):
        self.rm.shutdown()

orchestrator = Orchestrator()
