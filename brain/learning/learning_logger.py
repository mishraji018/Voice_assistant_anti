"""
learning_logger.py  –  Unknown-command logger and suggestion engine for Jarvis
===============================================================================
When Jarvis fails to understand a command:
  1. Logs the raw text + timestamp to jarvis_learning.json
  2. Suggests the closest known command based on shared keywords
  3. Exposes an easy-to-extend user_keywords.json for custom synonyms

Public API
----------
    from learning_logger import LearningLogger

    logger = LearningLogger()

    # Called when intent == "UNKNOWN"
    suggestions = logger.handle_unknown("khelo music aur chrome band karo")
    # Returns list[str] of suggestion strings to speak/display

    # Developers can add custom keywords in voice_assistant/user_keywords.json
"""

import json
import re
import os
import datetime
from typing import Optional

from core.infra.paths import JARVIS_LEARNING, USER_KEYWORDS

LEARNING_LOG_PATH  = JARVIS_LEARNING
USER_KEYWORDS_PATH = USER_KEYWORDS

# Max log entries to keep (avoids unbounded file growth)
MAX_LOG_ENTRIES = 500


# ─────────────────────────────────────────────────────────────────────────────
# Built-in keyword → intent suggestion table
# (These mirror keyword_engine.py but are intentionally standalone so this
#  module can be imported without the full keyword engine.)
# ─────────────────────────────────────────────────────────────────────────────
_SUGGESTION_MAP: list[tuple[set[str], str]] = [
    # (trigger_keywords, human-readable suggestion)
    ({"music", "song", "gana", "gaana", "play", "sunao", "bajao"},
     "play music → say 'play music' or 'gana chalao'"),

    ({"youtube", "video", "watch"},
     "open YouTube → say 'open youtube'"),

    ({"chrome", "firefox", "edge", "browser", "open"},
     "open an app → say 'open chrome' or 'open notepad'"),

    ({"search", "google", "find", "dhundo", "khojo"},
     "search the web → say 'search for <topic>'"),

    ({"time", "samay", "baje", "clock"},
     "get the time → say 'what time is it' or 'samay kya hai'"),

    ({"date", "aaj", "day", "today", "calendar"},
     "get the date → say 'aaj ki date' or 'what's the date'"),

    ({"weather", "mausam", "temperature", "forecast"},
     "check weather → say 'weather in <city>' or 'mausam batao'"),

    ({"news", "khabar", "samachar", "headline"},
     "get news → say 'latest news' or 'news batao'"),

    ({"note", "remind", "todo", "task", "reminder"},
     "set reminder → say 'remind me to <task>'"),

    ({"close", "band", "shut", "exit", "quit"},
     "close a window → say 'close window' or 'band karo'"),

    ({"volume", "mute", "louder", "quieter", "sound"},
     "adjust volume → say 'volume up' or 'mute'"),

    ({"screenshot", "capture", "screen"},
     "take screenshot → say 'take a screenshot'"),

    ({"shutdown", "restart", "reboot", "off"},
     "system control → say 'shutdown' or 'restart'"),

    ({"wifi", "internet", "net", "connection"},
     "toggle WiFi → say 'wifi on' or 'wifi off'"),

    ({"bluetooth", "bt", "pair"},
     "toggle Bluetooth → say 'bluetooth on'"),

    ({"joke", "funny", "laugh", "humor"},
     "hear a joke → say 'tell me a joke'"),

    ({"calculate", "math", "plus", "minus", "multiply"},
     "calculate → say 'calculate <expression>'"),

    ({"translate", "translate to", "meaning"},
     "translate → say 'translate <word> to Hindi'"),
]


# ─────────────────────────────────────────────────────────────────────────────
# LearningLogger class
# ─────────────────────────────────────────────────────────────────────────────

class LearningLogger:
    """
    Logs unrecognised commands and suggests the closest known action.

    Attributes
    ----------
    log_path          : path to jarvis_learning.json
    user_keywords_path: path to user_keywords.json (developer extension point)
    """

    def __init__(
        self,
        log_path: str = LEARNING_LOG_PATH,
        user_keywords_path: str = USER_KEYWORDS_PATH,
    ):
        self.log_path           = log_path
        self.user_keywords_path = user_keywords_path
        self._user_map          = self._load_user_keywords()

    # ── Public ────────────────────────────────────────────────────────────────

    def handle_unknown(self, text: str) -> list[str]:
        """
        Call this when intent == UNKNOWN.

        1. Logs the utterance to jarvis_learning.json.
        2. Returns a list of human-readable suggestion strings (may be empty).

        Parameters
        ----------
        text : the raw English (or translated) text of the failed command

        Returns
        -------
        list[str]  — 0–3 suggestion strings
        """
        self._log(text)
        suggestions = self._suggest(text)
        if suggestions:
            print(f"[Learning] Suggestions for '{text}': {suggestions}")
        return suggestions

    def get_log(self, limit: int = 20) -> list[dict]:
        """Return the last *limit* logged entries."""
        entries = self._read_log()
        return entries[-limit:]

    def get_log_count(self) -> int:
        """Return total number of logged unknown commands."""
        return len(self._read_log())

    def add_user_keyword(self, keyword: str, intent: str, entity: str = "") -> None:
        """
        Programmatically add a custom keyword mapping and save to user_keywords.json.
        Useful for extending Jarvis without editing source code.

        Parameters
        ----------
        keyword : trigger word/phrase (e.g. "khela", "game")
        intent  : target intent (e.g. "OPEN_APP")
        entity  : optional entity (e.g. "chrome")
        """
        self._user_map[keyword.lower()] = {"intent": intent, "entity": entity}
        self._save_user_keywords()
        print(f"[Learning] Added keyword: '{keyword}' → {intent}/{entity}")

    def lookup_user_keyword(self, text: str) -> Optional[dict]:
        """
        Check if any user-defined keyword appears in text.
        Returns {intent, entity} dict or None.
        """
        norm = text.lower()
        for kw, mapping in self._user_map.items():
            if kw in norm:
                return mapping
        return None

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, text: str) -> None:
        """Append an entry to the learning log JSON file."""
        entries = self._read_log()
        entries.append({
            "text"     : text,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        # Trim oldest entries if over limit
        if len(entries) > MAX_LOG_ENTRIES:
            entries = entries[-MAX_LOG_ENTRIES:]
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump({"unknown_commands": entries}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Learning] Log write error: {e}")

    def _read_log(self) -> list[dict]:
        """Read existing log file; return empty list on any error."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("unknown_commands", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    # ── Suggestion engine ─────────────────────────────────────────────────────

    def _suggest(self, text: str) -> list[str]:
        """
        Return up to 3 suggestion strings based on keyword overlap.
        Higher overlap → ranked higher.
        """
        norm   = re.sub(r"[^\w\s]", "", text.lower())
        tokens = set(norm.split())

        scored: list[tuple[int, str]] = []

        # Check built-in suggestions
        for keywords, suggestion in _SUGGESTION_MAP:
            overlap = len(tokens & keywords)
            if overlap > 0:
                scored.append((overlap, suggestion))

        # Check user-defined keywords
        for kw, mapping in self._user_map.items():
            if kw in norm:
                suggestion = f"custom command → '{kw}' (mapped to {mapping['intent']})"
                scored.append((2, suggestion))   # give user keywords a reasonable score

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:3]]

    # ── User keywords persistence ─────────────────────────────────────────────

    def _load_user_keywords(self) -> dict:
        """Load user_keywords.json; return empty dict if missing."""
        try:
            with open(self.user_keywords_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_user_keywords(self) -> None:
        """Persist user keyword map to user_keywords.json."""
        try:
            with open(self.user_keywords_path, "w", encoding="utf-8") as f:
                json.dump(self._user_map, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Learning] User keywords save error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

#: Shared singleton — import and use directly:
#:   from learning_logger import learner
learner = LearningLogger()


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== LearningLogger Demo ===\n")

    test_inputs = [
        "khelo kuch acha wala",
        "mujhe aaj kuch sunna hai",
        "browser pe jaana hai",
        "biryani recipe dhundo yaar",
        "screen capture karo jaldi",
        "laptop band ho jaye",
        "some totally unmappable gibberish xyz",
    ]

    for text in test_inputs:
        print(f"Input: {text!r}")
        suggestions = learner.handle_unknown(text)
        if suggestions:
            for s in suggestions:
                print(f"  → {s}")
        else:
            print("  → No suggestion found. Logged for review.")
        print()

    print(f"Total logged: {learner.get_log_count()} entries")
    print(f"Log file: {LEARNING_LOG_PATH}")
