"""
conversation_memory.py  -  Session + Persistent Memory for Jarvis
==================================================================
Two-layer memory:
  PERSISTENT  ->  jarvis_memory.json  (survives restarts)
                  stores: user_name, preferred_apps, facts, habits
  SESSION     ->  RAM only (cleared when Python exits)
                  stores: turn_history (last 20), last_command, last_topic

Public API
----------
    from conversation_memory import ConversationMemory

    mem = ConversationMemory()
    mem.remember("user_name", "Prateek")       # persist
    mem.recall("user_name")                    # -> "Prateek"
    mem.log_turn("user", "open chrome", "OPEN_APP")
    mem.recent_turns(3)                        # last 3 turns
    mem.answer_meta_query("what did I ask earlier?")
"""

import json
import os
import datetime
import re
from collections import deque

from core.infra.paths import JARVIS_MEMORY

# Where persistent facts are stored
MEMORY_FILE = JARVIS_MEMORY

MAX_SESSION_TURNS = 20   # keep last N turns in RAM


class ConversationMemory:

    def __init__(self):
        # ---- Persistent layer -----------------------------------------------
        self._persistent: dict = self._load()
        
        # Ensure default keys exist
        if "language" not in self._persistent:
            self._persistent["language"] = None  # None means unselected
        if "learned_mappings" not in self._persistent:
            self._persistent["learned_mappings"] = {}

        # ---- Session layer --------------------------------------------------
        self._turns: deque = deque(maxlen=MAX_SESSION_TURNS)
        self.last_command: str  = ""
        self.last_topic:   str  = ""
        self.session_start = datetime.datetime.now()
        self.session_language: str = self._persistent["language"]

    def get_language(self) -> str | None:
        """Return the user's preferred language ('en' or 'hi' or None)."""
        return self.session_language

    def set_language(self, lang: str) -> None:
        """Set and persist the user's language preference."""
        self.session_language = lang
        self.remember("language", lang)

    def learn_mapping(self, pattern: str, intent: str, entity: str = ""):
        """Store a user-corrected mapping for future use."""
        mappings = self.recall("learned_mappings", {})
        mappings[pattern.lower().strip()] = {"intent": intent, "entity": entity}
        self.remember("learned_mappings", mappings)

    # =========================================================================
    # Persistent memory
    # =========================================================================

    def _load(self) -> dict:
        """Load JSON from disk, return empty dict on first run."""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self) -> None:
        """Write persistent memory to disk."""
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._persistent, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Memory] Could not save: {e}")

    def remember(self, key: str, value) -> None:
        """Store a fact persistently (survives restarts)."""
        self._persistent[key] = value
        self._save()
        print(f"[Memory] Remembered: {key} = {value!r}")

    def recall(self, key: str, default=None):
        """Retrieve a persistent fact."""
        return self._persistent.get(key, default)

    def forget(self, key: str) -> None:
        """Remove a persistent fact."""
        self._persistent.pop(key, None)
        self._save()

    # =========================================================================
    # Session turn history
    # =========================================================================

    def log_turn(self, role: str, text: str, intent: str = "") -> None:
        """
        Log one dialogue turn.

        Parameters
        ----------
        role   : "user" or "jarvis"
        text   : the spoken/responded text
        intent : intent label if a command, or "CONVERSATION"
        """
        turn = {
            "role"     : role,
            "text"     : text,
            "intent"   : intent,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._turns.append(turn)

        # Track convenient shortcuts
        if role == "user":
            if intent and intent not in ("CONVERSATION", "UNKNOWN"):
                self.last_command = text
            if intent == "SEARCH_WEB":
                self.last_topic = text

    def recent_turns(self, n: int = 5) -> list:
        """Return the last n turns (oldest first)."""
        turns = list(self._turns)
        return turns[-n:] if n < len(turns) else turns

    def user_turns(self) -> list:
        """All user turns this session."""
        return [t for t in self._turns if t["role"] == "user"]

    def clear_session(self) -> None:
        """Reset session history (persistent memory unchanged)."""
        self._turns.clear()
        self.last_command = ""
        self.last_topic   = ""

    # =========================================================================
    # Meta-query answering
    # =========================================================================

    META_PATTERNS = [
        # What did I ask / say
        (r"what did i (ask|say|tell) you", "recall_asks"),
        (r"what was my last (command|request|question)", "recall_last_cmd"),
        # Name
        (r"what.?s my name|do you know my name|who am i", "recall_name"),
        # Session info
        (r"how long (have we|are we) (been talking|chatting)", "recall_duration"),
        (r"what did we talk about", "recall_summary"),
    ]

    def answer_meta_query(self, text: str) -> str | None:
        """
        Returns a natural-language answer to meta questions about memory.
        Returns None if the text is not a meta-query (caller should handle normally).
        """
        norm = text.lower().strip()

        for pattern, handler in self.META_PATTERNS:
            if re.search(pattern, norm):
                return getattr(self, f"_handle_{handler}")()

        return None

    # -- handlers --

    def _handle_recall_asks(self) -> str:
        user_turns = self.user_turns()
        if not user_turns:
            return "You haven't asked me anything yet this session."
        recent = [t["text"] for t in user_turns[-3:]]
        if len(recent) == 1:
            return f'You asked me: "{recent[0]}".'
        listed = " | ".join(f'"{t}"' for t in recent)
        return f"Your recent requests were: {listed}."

    def _handle_recall_last_cmd(self) -> str:
        if self.last_command:
            return f'Your last command was: "{self.last_command}".'
        return "I don't have a record of a previous command this session."

    def _handle_recall_name(self) -> str:
        name = self.recall("user_name")
        if name:
            return f"Your name is {name}."
        return "I don't know your name yet. You can tell me by saying 'My name is ...'."

    def _handle_recall_duration(self) -> str:
        delta = datetime.datetime.now() - self.session_start
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "We just started talking — less than a minute ago."
        return f"We've been talking for about {minutes} minute{'s' if minutes != 1 else ''}."

    def _handle_recall_summary(self) -> str:
        turns = self.user_turns()
        if not turns:
            return "We haven't discussed anything yet."
        topics = list({t["intent"] for t in turns if t["intent"] not in ("CONVERSATION", "UNKNOWN", "")})
        if topics:
            readable = ", ".join(t.replace("_", " ").lower() for t in topics)
            return f"We've talked about: {readable}."
        return "We've mostly been having a conversation."

    # =========================================================================
    # Convenience properties
    # =========================================================================

    @property
    def user_name(self) -> str:
        return self.recall("user_name", "")

    @property
    def session_length(self) -> int:
        """Number of turns this session."""
        return len(self._turns)
