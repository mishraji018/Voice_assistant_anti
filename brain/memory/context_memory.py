"""
context_memory.py  –  Lightweight context store for Jarvis
===========================================================
Remembers the last opened application/website so that follow-up commands
like "play song on that" or "search on it" can be resolved without the
user repeating the app name.

Public API
----------
    from context_memory import ContextMemory

    ctx = ContextMemory()

    # Record that Jarvis just opened YouTube
    ctx.set_app("youtube", url="https://youtube.com")

    # Resolve "on that" → "youtube"
    app = ctx.last_app          # "youtube"
    url = ctx.last_url          # "https://youtube.com"

    # Check whether a raw segment refers to the last app
    seg = ctx.resolve_reference("play song on that")
    # → "play song on youtube"

    # Full state dict (for logging / convo memory)
    ctx.to_dict()

Design Notes
------------
* Zero dependencies – pure Python stdlib only.
* Thread-safe via a simple lock (Jarvis uses threads for the wake-word loop).
* Persists only for the lifetime of the process (in-memory only).
  Add JSON / shelve serialisation here if cross-session memory is needed.
"""

import threading
import re

# ──────────────────────────────────────────────────────────────────────────────
# Reference patterns  →  "on that", "us par", "uss mein", etc.
# ──────────────────────────────────────────────────────────────────────────────

# English
_REF_PATTERNS_EN = [
    r"\bon\s+that\b",
    r"\bon\s+it\b",
    r"\bin\s+that\b",
    r"\bin\s+it\b",
    r"\busing\s+that\b",
    r"\busing\s+it\b",
    r"\bthere\b",
]

# Hinglish / Hindi
_REF_PATTERNS_HI = [
    r"\bus\s+par\b",
    r"\buss\s+par\b",
    r"\bus\s+mein\b",
    r"\buss\s+mein\b",
    r"\bwahan\b",
    r"\bwahan\s+par\b",
    r"\bukse\b",
    r"\buse\b",               # "ise" / "use" as pronoun
]

_ALL_REF_RE = re.compile(
    "|".join(_REF_PATTERNS_EN + _REF_PATTERNS_HI),
    flags=re.IGNORECASE,
)


class ContextMemory:
    """
    Thread-safe store for the last opened app / URL and intent.

    Attributes (read-only properties)
    ----------------------------------
    last_app    : str   – lowercase app/site name, e.g. "youtube"
    last_url    : str   – URL if the app is a website, else ""
    last_intent : str   – intent string of the last resolved action
    """

    def __init__(self):
        self._lock       = threading.Lock()
        self._last_app   = ""
        self._last_url   = ""
        self._last_intent = ""

    # ── Setters ───────────────────────────────────────────────────────────────

    def set_app(self, app_name: str, url: str = "", intent: str = "") -> None:
        """
        Record a newly opened application or website.

        Parameters
        ----------
        app_name : human-readable name, e.g. "youtube", "notepad"
        url      : URL if web-based, else empty string
        intent   : the intent that triggered this (e.g. "OPEN_APP", "OPEN_URL")
        """
        with self._lock:
            self._last_app    = app_name.lower().strip()
            self._last_url    = url.strip()
            self._last_intent = intent.strip()
        print(f"[ContextMemory] last_app='{self._last_app}' | "
              f"url='{self._last_url}' | intent='{self._last_intent}'")

    def clear(self) -> None:
        """Reset all context (e.g. at session start)."""
        with self._lock:
            self._last_app    = ""
            self._last_url    = ""
            self._last_intent = ""

    # ── Read-only properties ──────────────────────────────────────────────────

    @property
    def last_app(self) -> str:
        with self._lock:
            return self._last_app

    @property
    def last_url(self) -> str:
        with self._lock:
            return self._last_url

    @property
    def last_intent(self) -> str:
        with self._lock:
            return self._last_intent

    # ── Reference resolution ──────────────────────────────────────────────────

    def has_reference(self, text: str) -> bool:
        """Return True if *text* contains a contextual pronoun like 'on that'."""
        return bool(_ALL_REF_RE.search(text))

    def resolve_reference(self, text: str) -> str:
        """
        Replace contextual references ("on that", "us par" …) with the
        actual last_app name so the segment can be re-parsed cleanly.

        Example
        -------
        >>> ctx.set_app("youtube")
        >>> ctx.resolve_reference("play song on that")
        'play song on youtube'
        """
        if not self._last_app:
            return text   # nothing to substitute

        def replacer(m: re.Match) -> str:
            # Keep leading preposition (on / in / using / us / uss) if present
            matched = m.group(0).lower()
            # Strip the pronoun, keep preposition
            for pronoun in ("that", "it", "there", "wahan par", "wahan",
                            "ukse", "use", "mein", "par"):
                if matched.endswith(pronoun):
                    prefix = matched[: -len(pronoun)].rstrip()
                    sep    = " " if prefix else ""
                    return f"{prefix}{sep}{self._last_app}"
            return self._last_app   # fallback: replace whole match

        resolved = _ALL_REF_RE.sub(replacer, text)
        print(f"[ContextMemory] Resolved ref: '{text}' → '{resolved}'")
        return resolved

    # ── Utility ───────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return current context as a plain dict (useful for logging)."""
        with self._lock:
            return {
                "last_app"   : self._last_app,
                "last_url"   : self._last_url,
                "last_intent": self._last_intent,
            }

    def __repr__(self) -> str:
        return (f"ContextMemory(last_app='{self.last_app}', "
                f"last_url='{self.last_url}')")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton  –  import and use directly if preferred
# ─────────────────────────────────────────────────────────────────────────────

#: Shared singleton for use across modules without passing the object around.
#: Import it as:  from context_memory import ctx_mem
ctx_mem = ContextMemory()
