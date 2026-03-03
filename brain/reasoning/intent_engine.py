"""
intent_engine.py – Improved rule-based NLP intent classifier
============================================================
Upgrades:
• Better CLOSE detection ("close screen", "close browser", etc.)
• Stronger entity extraction
• Hinglish-friendly matching
• Prevents greetings from overriding commands
"""

import re
from typing import Dict

# ---------------------------------------------------------------------------
# 1. Intent definitions
# ---------------------------------------------------------------------------

INTENT_RULES = [

    # ───────── OPEN APP ─────────
    (
        "OPEN_APP",
        ["open", "start", "launch", "run", "execute", "kholo", "chalu"],
        ["open", "start", "launch", "run", "execute"],
        0.7,
    ),

    # ───────── CLOSE WINDOW / APP ─────────
    (
        "CLOSE_WINDOW",
        [
            "close window", "close screen", "close app", "close tab",
            "band karo", "band kar do", "screen band karo",
            "exit app", "quit app", "close browser"
        ],
        ["close", "exit", "quit", "band", "shut"],
        0.75,
    ),

    # ───────── SEARCH ─────────
    (
        "SEARCH_WEB",
        ["search", "google", "find", "look", "browse", "dhundo"],
        ["search", "google", "find", "look", "browse", "internet"],
        0.6,
    ),

    # ───────── SYSTEM CONTROL ─────────
    (
        "SYSTEM_CONTROL",
        ["shutdown", "restart", "lock", "screenshot", "volume", "wifi"],
        ["shutdown", "restart", "lock", "wifi", "bluetooth", "volume", "screenshot"],
        0.7,
    ),

    # ───────── MEDIA ─────────
    (
        "MEDIA_CONTROL",
        ["play", "pause", "music", "song", "video", "youtube"],
        ["play", "pause", "stop", "music", "song", "video", "youtube"],
        0.65,
    ),

    # ───────── INFO ─────────
    (
        "INFO_QUERY",
        ["time", "weather", "date", "battery", "stock"],
        ["time", "weather", "date", "battery", "stock"],
        0.6,
    ),

    # ───────── NOTE / TASK ─────────
    (
        "NOTE_TASK",
        ["note", "remind", "task", "todo", "remember"],
        ["note", "remind", "task", "todo", "alarm"],
        0.6,
    ),

    # ───────── CALCULATOR ─────────
    (
        "CALCULATOR",
        ["calculate", "solve", "plus", "minus", "multiply", "divide"],
        ["calculate", "plus", "minus", "multiply", "divide"],
        0.7,
    ),

    # ───────── NEWS ─────────
    (
        "NEWS",
        ["news", "headline", "khabar", "samachar"],
        ["news", "headline", "khabar", "samachar"],
        0.65,
    ),

    # ───────── SMALL TALK (lowest priority) ─────────
    (
        "SMALL_TALK",
        ["hello", "hi", "hey", "thanks", "bye", "who are you"],
        ["hello", "hi", "hey", "thanks", "bye"],
        0.2,
    ),
]


# ---------------------------------------------------------------------------
# 2. Known app names
# ---------------------------------------------------------------------------

APP_NAMES = [
    "chrome", "edge", "firefox", "notepad", "calculator",
    "word", "excel", "powerpoint", "vscode", "paint",
    "explorer", "spotify", "vlc", "discord", "teams"
]


# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _extract_entity(text: str, intent: str) -> str:

    # --- App detection ---
    for app in APP_NAMES:
        if app in text:
            return app

    # --- Word after action ---
    m = re.search(r"(?:open|start|launch|run|close|search)\s+(\w+)", text)
    if m:
        return m.group(1)

    # --- Search query fallback ---
    if intent == "SEARCH_WEB":
        cleaned = re.sub(r"\b(search|google|find|look)\b", "", text).strip()
        return cleaned

    return ""


# ---------------------------------------------------------------------------
# 4. Main classifier
# ---------------------------------------------------------------------------

def detect_intent(nlp_data) -> str:
    """
    Detects the intent from either a raw string or the NLP pipeline dictionary.
    """
    # If it's a dict from nlp_pipeline.process_text
    if isinstance(nlp_data, dict):
        if nlp_data.get("intent_result") and nlp_data["intent_result"].get("intent"):
            return nlp_data["intent_result"]["intent"]
        text = nlp_data.get("text", nlp_data.get("raw", ""))
    else:
        text = nlp_data

    if not text:
        return "UNKNOWN"

    norm = _normalise(text)

    # --- Exact phrase detection first ---
    for intent, phrases, _kw, _w in INTENT_RULES:
        for ph in phrases:
            if ph in norm:
                return {
                    "intent": intent,
                    "entity": _extract_entity(norm, intent),
                    "confidence": 1.0,
                    "raw": norm,
                }

    # --- Keyword scoring ---
    tokens = set(norm.split())
    scores = {}

    for intent, _phrases, keywords, weight in INTENT_RULES:
        hits = sum(1 for k in keywords if k in tokens)
        if hits:
            scores[intent] = hits * weight

    if scores:
        best = max(scores, key=scores.get)
        return {
            "intent": best,
            "entity": _extract_entity(norm, best),
            "confidence": round(min(scores[best], 1.0), 2),
            "raw": norm,
        }

    return {"intent": "UNKNOWN", "entity": "", "confidence": 0.0, "raw": norm}