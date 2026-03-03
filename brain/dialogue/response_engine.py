"""
response_engine.py  –  Conversational, randomised response generator
=====================================================================
Provides human-like feedback after every Jarvis action.

Usage
-----
    from response_engine import confirm, error_response, greet
    speak(greet(9))               # "Good morning! Ready to help you today."
    speak(confirm("OPEN_APP", "Chrome"))  # "Opening Chrome right away!"
    speak(error_response())       # "Hmm, I didn't quite get that…"
"""

import random
from collections import deque

# ---------------------------------------------------------------------------
# LRU phrase tracker – prevents repeating the last 2 responses per category
# ---------------------------------------------------------------------------
_last_used: dict[str, deque] = {}


def _pick(category: str, pool: list[str]) -> str:
    """Return a random phrase from pool, avoiding recent repeats."""
    history = _last_used.setdefault(category, deque(maxlen=2))
    available = [p for p in pool if p not in history] or pool
    choice = random.choice(available)
    history.append(choice)
    return choice


# ---------------------------------------------------------------------------
# Response pools  (4–6 variants per intent)
# ---------------------------------------------------------------------------

_POOLS: dict[str, list[str]] = {

    # ── App opening ─────────────────────────────────────────────────────────
    "OPEN_APP": [
        "Opening {entity} right away!",
        "Sure, launching {entity} for you.",
        "Let me start {entity}… one moment.",
        "{entity} is on its way!",
        "Got it — opening {entity} now.",
        "Sure thing, starting {entity}!",
    ],

    # ── Close / window ───────────────────────────────────────────────────────
    "CLOSE_WINDOW": [
        "Closing that window now.",
        "Sure, shutting it down.",
        "Done — window closed.",
        "Closing it for you.",
        "Alright, that's closed.",
    ],

    # ── Web search ───────────────────────────────────────────────────────────
    "SEARCH_WEB": [
        "Searching for {entity} on the web.",
        "Let me look that up — {entity}.",
        "Sure, googling {entity} now.",
        "Here we go, searching for {entity}.",
        "On it! Looking up {entity}.",
    ],

    # ── System control ───────────────────────────────────────────────────────
    "SYSTEM_CONTROL": [
        "Executing your system command.",
        "Done — system command applied.",
        "Alright, taking care of that.",
        "Sure, handling that right now.",
        "System action completed.",
    ],

    # ── Media ────────────────────────────────────────────────────────────────
    "MEDIA_CONTROL": [
        "Playing your music now!",
        "Sure, let's get some tunes going.",
        "Media control — done!",
        "Alright, handling your media.",
        "Got it, entertainment mode activated.",
    ],

    # ── Info / query ─────────────────────────────────────────────────────────
    "INFO_QUERY": [
        "Let me check that for you.",
        "Sure, fetching the information now.",
        "Here's what I found for {entity}.",
        "Hold on, getting that for you.",
        "On it — pulling up the details.",
    ],

    # ── Notes / tasks ────────────────────────────────────────────────────────
    "NOTE_TASK": [
        "Got it, I've noted that down.",
        "Done — reminder set.",
        "Sure, adding that to your list.",
        "Task saved! Anything else?",
        "Noted. I'll remind you.",
    ],

    # ── Calculator ───────────────────────────────────────────────────────────
    "CALCULATOR": [
        "Crunching the numbers for you.",
        "Let me calculate that.",
        "Here's the result for {entity}.",
        "Sure, solving that right now.",
        "Math mode — activated!",
    ],

    # ── News ─────────────────────────────────────────────────────────────────
    "NEWS": [
        "Fetching the latest headlines!",
        "Sure, here's what's happening in the world.",
        "Let me pull up today's news for you.",
        "Loading the latest stories.",
        "Here are your top headlines.",
    ],

    # ── Small talk ───────────────────────────────────────────────────────────
    "SMALL_TALK": [
        "Thanks for chatting! How can I help?",
        "Always happy to talk! What do you need?",
        "I'm doing great, ready to assist you!",
        "Hey there! Ready when you are.",
        "Good to hear from you. What's up?",
    ],

    # ── Unknown / fallback ───────────────────────────────────────────────────
    "UNKNOWN": [
        "I'm sorry, I didn't quite get that. Could you rephrase?",
        "Hmm, I didn't understand that. Try again?",
        "I'm not sure what you meant — could you say it differently?",
        "That one slipped past me. Can you repeat more clearly?",
        "I didn't catch your intent — please try again.",
    ],

    # ── Errors ───────────────────────────────────────────────────────────────
    "ERROR": [
        "Oops, something went wrong. Let me try again.",
        "I ran into a small issue. My apologies!",
        "Sorry, there was a hiccup. Please try again.",
        "An error occurred — I'm sorry about that.",
        "Something didn't work as expected. Want to retry?",
    ],
}

# ── Greetings keyed by hour-of-day range ────────────────────────────────────
_GREETINGS: dict[str, list[str]] = {
    "morning": [
        "Good morning! Ready to power through your day?",
        "Rise and shine! How can I help you today?",
        "Good morning! What can I do for you?",
        "Morning! I'm all set whenever you are.",
    ],
    "afternoon": [
        "Good afternoon! How can I assist you?",
        "Hey there — good afternoon! What do you need?",
        "Good afternoon! I'm here and ready.",
        "Afternoon! What can I help you with?",
    ],
    "evening": [
        "Good evening! Hope your day went well. How can I help?",
        "Evening! Ready to assist you.",
        "Good evening — what can I do for you?",
        "Hey, good evening! What's on your mind?",
    ],
    "night": [
        "Working late? I'm here to help!",
        "Good night owl mode — activated! How can I help?",
        "Hi there! Even at this hour, I'm ready.",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def confirm(intent: str, entity: str = "") -> str:
    """
    Return a randomised confirmation phrase for the given intent.

    Parameters
    ----------
    intent : e.g. "OPEN_APP"
    entity : optional subject (app name, search query, etc.)
    """
    pool = _POOLS.get(intent, _POOLS["UNKNOWN"])
    phrase = _pick(intent, pool)
    # Substitute {entity} placeholder if present
    if entity:
        phrase = phrase.replace("{entity}", entity.title())
    else:
        phrase = phrase.replace(" for {entity}", "").replace("{entity}", "that").strip()
    return phrase


def error_response() -> str:
    """Return a randomised error/apology phrase."""
    return _pick("ERROR", _POOLS["ERROR"])


def greet(hour: int) -> str:
    """
    Return a time-aware randomised greeting.

    Parameters
    ----------
    hour : 0–23  (use datetime.datetime.now().hour)
    """
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 21:
        period = "evening"
    else:
        period = "night"
    return _pick(f"greet_{period}", _GREETINGS[period])


# ── Conversational Orchestrator ─────────────────────────────────────────────

def format_response(result: str, plan: dict) -> str:
    """
    Wraps results into natural sounding conversational phrases.
    """
    action = plan.get("action")
    
    prefixes = {
        "web_search": [
            "Just a moment, fetching the latest info…",
            "Let me check the web for you…",
            "Hold on, I'm looking that up right now.",
            "Fetching the latest information on that…"
        ],
        "command": [
            "Done. Here's the result.",
            "Sure, I've handled that for you.",
            "On it! Here is what I found.",
            "Executing now... all set."
        ],
        "answer": [
            "Here's what I know…",
            "Based on my knowledge…",
            "Good question! Here's the answer.",
            "I've got an answer for you."
        ]
    }
    
    prefix = random.choice(prefixes.get(action, ["Here you go…"]))
    return f"{prefix} {result}"
