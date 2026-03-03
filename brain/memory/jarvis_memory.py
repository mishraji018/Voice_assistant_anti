"""
jarvis_memory.py  –  Persistent user memory for Jarvis
=======================================================
Stores and recalls:
  • user name
  • preferred apps
  • last command
  • arbitrary preferences ("Remember that I use Chrome")

Data persists in  jarvis_memory.json  next to this file.

Public API
----------
    from jarvis_memory import mem

    mem.set_name("Alice")
    mem.get_name()                     # "Alice"
    mem.remember("browser", "Chrome")
    mem.recall("browser")              # "Chrome"
    mem.set_last_command("open chrome")
    mem.get_last_command()             # "open chrome"
    mem.all_preferences()             # {"browser": "Chrome", …}

    # High-level NL handlers (call from command pipeline)
    result = mem.handle_remember_command("remember that I use Chrome")
    result = mem.handle_recall_command("what is my browser")
    result = mem.handle_name_command("my name is Alice")
"""

import json
import re
import threading
from core.infra.paths import JARVIS_MEMORY

_MEMORY_FILE = JARVIS_MEMORY

# ── Default schema ────────────────────────────────────────────────────────────
_DEFAULTS = {
    "name"        : "",
    "last_command": "",
    "preferences" : {},   # key → value  (e.g. "browser" → "Chrome")
    "fav_apps"    : [],   # list of app names
}


class JarvisMemory:
    """Thread-safe persistent memory store."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(_DEFAULTS)
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if _MEMORY_FILE.exists():
            try:
                with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Merge saved keys so new defaults are added gracefully
                for k, v in _DEFAULTS.items():
                    self._data[k] = saved.get(k, v)
            except Exception as exc:
                print(f"[Memory] Could not load memory: {exc}")

    def _save(self) -> None:
        try:
            with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"[Memory] Could not save memory: {exc}")

    # ── Name ──────────────────────────────────────────────────────────────────

    def set_name(self, name: str) -> None:
        with self._lock:
            self._data["name"] = name.strip().title()
            self._save()

    def get_name(self) -> str:
        with self._lock:
            return self._data["name"]

    # ── Last command ──────────────────────────────────────────────────────────

    def set_last_command(self, cmd: str) -> None:
        with self._lock:
            self._data["last_command"] = cmd
            self._save()

    def get_last_command(self) -> str:
        with self._lock:
            return self._data["last_command"]

    # ── Preferences ───────────────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> None:
        """Store an arbitrary preference."""
        with self._lock:
            self._data["preferences"][key.lower().strip()] = value.strip()
            self._save()

    def recall(self, key: str) -> str:
        """Retrieve a preference by key. Returns '' if not found."""
        with self._lock:
            return self._data["preferences"].get(key.lower().strip(), "")

    def all_preferences(self) -> dict:
        with self._lock:
            return dict(self._data["preferences"])

    # ── Favourite apps ────────────────────────────────────────────────────────

    def add_fav_app(self, app: str) -> None:
        with self._lock:
            name = app.strip().title()
            if name not in self._data["fav_apps"]:
                self._data["fav_apps"].append(name)
                self._save()

    def get_fav_apps(self) -> list:
        with self._lock:
            return list(self._data["fav_apps"])

    # ── Natural-language command handlers ─────────────────────────────────────

    def handle_name_command(self, text: str) -> str:
        """
        Detect "my name is X" or "call me X" and store the name.
        Returns a confirmation string, or "" if not matched.
        """
        text = text.lower().strip()
        patterns = [
            r"my name is ([a-z]+)",
            r"call me ([a-z]+)",
            r"i am ([a-z]+)",
            r"mera naam ([a-z]+) hai",
            r"mera naam ([a-z]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                name = m.group(1).title()
                self.set_name(name)
                return f"Got it! I'll remember you as {name}."
        return ""

    def handle_remember_command(self, text: str) -> str:
        """
        Detect "remember that I use/prefer X" patterns.
        Maps common phrases to a key-value preference.
        Returns a confirmation string, or "" if not matched.
        """
        text_l = text.lower().strip()

        # "Remember that I use/prefer/like X"
        m = re.search(
            r"remember (?:that )?(?:i |my )?"
            r"(?:use|prefer|like|favourite is|favorite is|love)\s+(.+)",
            text_l,
        )
        if m:
            value = m.group(1).strip().title()
            # Guess key from the value (best-effort)
            key = _guess_pref_key(value)
            self.remember(key, value)
            return f"Noted! I'll remember that you prefer {value}."

        # "My favourite/preferred X is Y"
        m = re.search(
            r"my (?:favourite|favorite|preferred|default)\s+(\w+)\s+is\s+(.+)",
            text_l,
        )
        if m:
            key   = m.group(1).strip()
            value = m.group(2).strip().title()
            self.remember(key, value)
            return f"Got it — your {key} is {value}."

        return ""

    def handle_recall_command(self, text: str) -> str:
        """
        Detect "what is my name / what is my X" and return stored value.
        Returns the spoken answer, or "" if not matched.
        """
        text_l = text.lower().strip()
        name   = self.get_name()

        # Name query
        if any(p in text_l for p in ["what is my name", "what's my name",
                                      "mera naam kya hai", "do you know my name"]):
            if name:
                return f"Your name is {name}."
            return "I don't know your name yet. Please tell me."

        # Last command
        if "last command" in text_l or "what did i say" in text_l:
            last = self.get_last_command()
            return f"Your last command was: {last}." if last else "I don't recall your last command."

        # Preference query  "what is my browser / what browser do I use"
        m = re.search(r"what(?:'s| is) my (\w+)", text_l)
        if m:
            key = m.group(1).strip()
            val = self.recall(key)
            if val:
                return f"Your {key} is {val}."
            return f"I don't have a preference saved for {key} yet."

        return ""


def _guess_pref_key(value: str) -> str:
    """Map a preference value to a sensible key."""
    v = value.lower()
    if any(x in v for x in ["chrome", "firefox", "edge", "brave", "opera"]):
        return "browser"
    if any(x in v for x in ["spotify", "youtube", "gaana", "wynk", "jio saavn"]):
        return "music"
    if any(x in v for x in ["vs code", "vscode", "pycharm", "notepad"]):
        return "editor"
    if any(x in v for x in ["gmail", "outlook", "yahoo"]):
        return "email"
    return "app"


# ── Module singleton ──────────────────────────────────────────────────────────
mem = JarvisMemory()
