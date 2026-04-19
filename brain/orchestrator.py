
import os
import sys
import time
import random
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

# ── Constants ────────────────────────────────────────────────────────────────
WAKE_PHRASES = ["jarvis", "hello jarvis", "hi jarvis", "listen jarvis", "hey jarvis"]
REPEAT_KEYWORDS = ["repeat", "wapas", "firse", "fir se", "again", "pardon", "kya bola", "once more", "kya?", "kya"]
STOP_WORDS = ["stop", "ruko", "bas", "cancel", "band karo"]
FOLLOWUP_WINDOW = 10.0 # seconds
WELLNESS_COOLDOWN = 600 # 10 minutes

def _contains_stop(text: str) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in STOP_WORDS)


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
        response = "Hi, I am Jarvis. Kya madad kar sakta hoon aapki?"
        bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
        self.rm.speak(response, use_female=False)

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
        if _contains_stop(text):
            state.request_stop()
            bus.emit("FORCE_STOP", {}) 
            response = "Sir kya hua? Kuch aur search karna hai aapko? Main yahi hoon."
            if ui:
                ui.set_message(response, "#ffab40")
                ui.set_subtitle("")
            bus.emit("SPEECH_REQUESTED", {"text": response, "ui_state": "SPEAKING"})
            self.rm.speak(response, use_female=False)
            state.clear_stop()
            if ui:
                ui.set_state("IDLE")
                ui.clear_message()
            return

        # ── Wake check ────────────────────────────────────────────────────────
        current_time_val = time.time()
        is_in_followup = (current_time_val - state.last_activity_time) < FOLLOWUP_WINDOW
        
        has_wake = False
        cleaned_text = text.strip().lower()
        
        # Explicit wake-word check
        for phrase in WAKE_PHRASES:
            if phrase in cleaned_text:
                has_wake = True
                if cleaned_text.startswith(phrase): cleaned_text = cleaned_text[len(phrase):].strip()
                elif cleaned_text.endswith(phrase): cleaned_text = cleaned_text[:cleaned_text.rfind(phrase)].strip()
                break
        
        if is_in_followup: has_wake = True
            
        if not has_wake:
            if ui: 
                ui.set_state("IDLE")
                ui.set_subtitle("Listening for 'Jarvis'...")
            return

        state.last_activity_time = current_time_val

        # ── Smart Repeat Check ────────────────────────────────────────────────
        if is_in_followup and any(kw in cleaned_text for kw in REPEAT_KEYWORDS) and state.last_response:
             if "jarvis" not in text.lower():
                if ui: ui.set_subtitle("Repeating last response...")
                self.rm.speak(state.last_response, use_female=state.last_response_use_female)
                state.last_activity_time = time.time()
                return

        if cleaned_text: text = cleaned_text
        else:
            response = "Sir main yahi hoon. Bas order dijiye."
            self.rm.speak(response, use_female=False)
            return

        state.clear_stop()

        if ui:
            ui.set_state("THINKING")
            ui.set_subtitle("Thinking...")

        # ── 1. Get History Context ────────────────────────────────────────────
        history = memory.get_history_string()

        # 2. Translate / Intent Detection
        start_time = time.time()
        english_text = translate_to_english(text, "auto")
        trans_time = time.time() - start_time
        
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
                         self.rm.speak(f"Sir, maine seekh liya hai. Agli baar se '{state.last_query}' bypass ho jayega.", use_female=False)
                         return

        intent_start = time.time()
        result = detect_intent(english_text)
        intent = learned_intent if learned_intent else result["intent"]
        entity = result["entity"]
        detect_time = time.time() - intent_start
        
        # Save for learning next turn
        state.last_query = english_text
        state.last_intent = intent
        
        print(f"[Brain] Intent: {intent} (Learned: {bool(learned_intent)}) | Entity: {entity}")
        print(f"[Profiling] Translation: {trans_time:.3f}s | Intent: {detect_time:.3f}s", flush=True)

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
            if ui: ui.set_subtitle(f"Executing: {english_text}...")
            response_text = command_system.run(english_text)
        elif intent == "SMALL_TALK":
            # ── 0c. Daily Wellness Check-in ──────────────────────────────────────
            # Trigger ONLY during small talk and ONLY once a day
            import datetime
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            if state.last_checkin_dt != today_str:
                state.last_checkin_dt = today_str
                checkin_msg = "Good morning sir! Aaj aapne apna wellness routine start kiya? Pani kitna piya hai abhi tak? Aur sir, kya aapne aaj exercise ki ya kal raat ki neend kaise rahi?"
                self.rm.speak(checkin_msg, use_female=False)
            
            response_text = "Always a pleasure to help, sir."
            if "who are you" in text.lower() or "kaun ho" in text.lower():
                response_text = "I am Jarvis, your smart Hindi-English personal assistant. Main apki help ke liye hamesha taiyar hoon, sir."
        elif intent == "INFO_QUERY":
            # ── Direct info lookup: 'who is X', 'what is X', 'tell me about X' ──
            if ui: ui.set_subtitle("Looking that up...")
            response_text = get_answer(english_text, history=history)
        
        if not response_text and not state.is_stop_requested():
            if ui: ui.set_subtitle("Searching Memory...")
            
            brain_start = time.time()
            # [Optimization] Pass original raw text to catch Hinglish nuances directly (Fills 'Ultra-Fast' requirement)
            # This skips GoogleTrans delay for the Brain.
            response_text = get_answer(text, history=history) 
            brain_time = time.time() - brain_start
            print(f"[Profiling] AI Brain (Flash Mode): {brain_time:.3f}s", flush=True)

        # ── 5. finalize and Save Turn ─────────────────────────────────────────
        if response_text and not state.is_stop_requested():
            # Save to memory for follow-up
            memory.add_turn(text, response_text)
            
            # Cache for Smart Repeat
            state.last_response = response_text
            state.last_response_use_female = False
            state.last_activity_time = time.time()
            
            # Emit event first so UI shows text
            bus.emit("SPEECH_REQUESTED", {"text": response_text, "ui_state": "SPEAKING"})
            
            # Use STREAMING speech for long responses
            if len(response_text) > 60:
                self.rm.speak_streaming(response_text)
            else:
                self.rm.speak(response_text)

        # ── 8. Wellness Reminder — throttled to max once per 10 minutes ─────
        # Only reminds the user if at least 10 minutes have passed since the last one.
        now = time.time()
        last_reminder = getattr(state, 'last_wellness_reminder_ts', 0)
        if (now - last_reminder) > 600 and random.random() < 0.20:
            reminder = random.choice([
                "Sir, thoda pani peelijiye, hydration zaroori hai.",
                "Sir, thoda break lekar walk kar lijiye, it's good for health.",
                "Sir, neend achhi lijiye aaj raat, recovery ke liye important hai."
            ])
            self.rm.speak(reminder, use_female=False)
            state.last_wellness_reminder_ts = now

        if ui: ui.set_state("IDLE")

    def handle_stop(self, _):
        self.rm.shutdown()

orchestrator = Orchestrator()
