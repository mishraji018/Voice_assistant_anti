"""
connectivity_checker.py  –  Internet connectivity guard
=========================================================
Uses a raw socket TCP connect to Google's DNS (8.8.8.8:53) —
no HTTP library, no DNS lookup, works even when DNS itself is broken.

Public API
----------
    from connectivity_checker import is_online, require_internet, INTERNET_INTENTS

    if not is_online():
        speak("No internet")

    # Guard before any internet-dependent command:
    if intent in INTERNET_INTENTS:
        if not require_internet(speak):
            continue   # skip command, user already notified
"""

import socket

# ── Intents that need internet ─────────────────────────────────────────────
INTERNET_INTENTS: set[str] = {
    "SEARCH_WEB",
    "NEWS",
    # INFO_QUERY sub-topics that need internet
    # (weather, stock)  — checked separately in require_internet()
}

# INFO_QUERY entity keywords that require internet
INTERNET_INFO_ENTITIES: set[str] = {"weather", "stock", "horoscope"}

# ── Hinglish offline message ───────────────────────────────────────────────
_OFFLINE_MSG = (
    "O… o… lagta hai aap internet se connected nahi ho. "
    "Pehle network connect kariye."
)

_OFFLINE_MSG_ENGLISH = (
    "It seems you're not connected to the internet. "
    "Please connect to a network first."
)


def is_online(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
    """
    Return True if a TCP connection to host:port succeeds within timeout seconds.
    Default target is Google Public DNS — highly reliable, ultra-fast check.
    """
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def require_internet(speak, intent: str = "", entity: str = "") -> bool:
    """
    Check connectivity and notify the user if offline.

    Parameters
    ----------
    speak  : TTS speak callable
    intent : current intent string (used for context-aware checks)
    entity : extracted entity (used to check weather/stock for INFO_QUERY)

    Returns
    -------
    True  — internet is available, proceed with command
    False — no internet, user notified, caller should skip command
    """
    # Fast-path: always check
    if not is_online():
        print("[Connectivity] ❌ No internet detected.")
        # Speak in Hinglish first, then English for clarity
        speak(_OFFLINE_MSG)
        return False

    print("[Connectivity] ✅ Internet available.")
    return True


def needs_internet(intent: str, entity: str = "") -> bool:
    """
    Return True if this intent+entity combination requires internet.
    Use this in main.py to decide whether to call require_internet().

    Examples
    --------
    needs_internet("SEARCH_WEB")            → True
    needs_internet("INFO_QUERY", "weather") → True
    needs_internet("INFO_QUERY", "time")    → False  (local)
    needs_internet("OPEN_APP", "chrome")    → False
    """
    if intent in INTERNET_INTENTS:
        return True
    if intent == "INFO_QUERY" and entity.lower() in INTERNET_INFO_ENTITIES:
        return True
    if intent == "MEDIA_CONTROL" and "youtube" in entity.lower():
        return True
    return False


def connectivity_status() -> dict:
    """
    Return a detailed connectivity status dict for debugging.
    """
    online = is_online()
    return {
        "online"  : online,
        "message" : "Connected" if online else _OFFLINE_MSG_ENGLISH,
    }
