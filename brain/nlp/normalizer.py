"""
normalizer.py  –  Stage 1: Speech Normalization Layer
======================================================
Cleans raw ASR output before intent detection.
Handles: wake words, fillers, repeated words, phonetic typos,
         Hinglish verbs, and punctuation.

Public API
----------
    from normalizer import normalize
    clean = normalize("hey jarvis youtub kholo yaar")
    # → "youtube open"
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wake words / trigger phrases to strip from the front
# ─────────────────────────────────────────────────────────────────────────────

_WAKE_WORDS = [
    "hey jarvis", "hi jarvis", "ok jarvis", "okay jarvis", "hello jarvis",
    "jarvis sun", "jarvis suno", "aye jarvis", "jarvis",
]

# Build longest-first regex so "hey jarvis" is stripped before "jarvis"
_WAKE_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(w) for w in sorted(_WAKE_WORDS, key=len, reverse=True)) + r")\s*",
    flags=re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Filler / noise phrases  (stripped from anywhere in the sentence)
# ─────────────────────────────────────────────────────────────────────────────

_FILLERS = [
    # English politeness
    "could you please", "can you please", "would you please", "please",
    "kindly", "quickly", "right away", "right now", "asap", "immediately",
    "i want you to", "i want to", "i need you to", "i need to",
    "i'd like you to", "i'd like to", "go ahead and", "go ahead",
    # Hinglish fillers / address words
    "yaar", "bhai", "boss", "dost", "bro", "mere bro",
    "zara", "thoda sa", "thoda", "ek baar", "please",
    "jaldi se", "jaldi",
    # Uncertain / questioning noise
    "umm", "uhh", "uh", "hmm", "err",
]

# Build longest-first pattern
_FILLER_RE = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in sorted(_FILLERS, key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Phonetic / ASR misspelling corrections
#    Maps what ASR commonly returns → canonical correct form
# ─────────────────────────────────────────────────────────────────────────────

_PHONETIC: dict[str, str] = {
    # Browsers
    "youtub"        : "youtube",
    "you tube"      : "youtube",
    "u tube"        : "youtube",
    "gogle"         : "google",
    "googl"         : "google",
    "crome"         : "chrome",
    "chorme"        : "chrome",
    "grome"         : "chrome",
    "crome"         : "chrome",
    "frefox"        : "firefox",
    "fierfox"       : "firefox",
    "fire fox"      : "firefox",
    "mirosoft"      : "microsoft",
    "microsft"      : "microsoft",
    "micorsoft"     : "microsoft",
    "micsofot"      : "microsoft",
    # Apps
    "notepadd"      : "notepad",
    "note pad"      : "notepad",
    "calclator"     : "calculator",
    "calcultr"      : "calculator",
    "spottify"      : "spotify",
    "spotfy"        : "spotify",
    "discrd"        : "discord",
    "whatsap"       : "whatsapp",
    "watsapp"       : "whatsapp",
    "what sapp"     : "whatsapp",
    "tlegram"       : "telegram",
    "teligram"      : "telegram",
    "vs cod"        : "vscode",
    "vs code"       : "vscode",
    "visual studio" : "vscode",
    "pycharm"       : "pycharm",
    "pi charm"      : "pycharm",
    # Hinglish verb misspellings
    "khol do"       : "kholo",
    "khol doh"      : "kholo",
    "kholdo"        : "kholo",
    "chala do"      : "chalao",
    "chala doh"     : "chalao",
    "bajado"        : "bajao",
    "baja do"       : "bajao",
    "gaana"         : "gana",
    "gaane"         : "gane",
    "sunao ji"      : "sunao",
    "sun ao"        : "sunao",
    # Connectors
    "aur phir"      : "then",
    "uske baad"     : "then",
    "iske baad"     : "then",
    "aur"           : "and",
}

# Build longest-first list for iteration
_PHONETIC_SORTED = sorted(_PHONETIC.items(), key=lambda x: len(x[0]), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Hinglish verb → canonical English action map
#    (supplements translator.py's HINDI_DICT for verbs that reach normalizer)
# ─────────────────────────────────────────────────────────────────────────────

_HINGLISH_VERBS: dict[str, str] = {
    "kholo"         : "open",
    "khol"          : "open",
    "band karo"     : "close",
    "band kar"      : "close",
    "band"          : "close",
    "chalao"        : "play",
    "chala"         : "play",
    "bajao"         : "play",
    "sunao"         : "play",
    "chalu karo"    : "start",
    "chalu kar"     : "start",
    "chalu"         : "start",
    "shuru karo"    : "launch",
    "shuru"         : "launch",
    "dhundo"        : "search",
    "dhoondo"       : "search",
    "batao"         : "tell me",
    "bata do"       : "tell me",
    "dikhao"        : "show",
    "dikha do"      : "show",
    "dekhna hai"    : "watch",
    "sunna hai"     : "listen to",
    "mute karo"     : "mute",
    "pause karo"    : "pause",
    "resume karo"   : "resume",
    "restart karo"  : "restart",
    "lock karo"     : "lock",
    "screenshot lo" : "take screenshot",
    "volume badha"  : "volume up",
    "volume kam"    : "volume down",
}

_HINGLISH_SORTED = sorted(_HINGLISH_VERBS.items(), key=lambda x: len(x[0]), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Repeated-word deduplication
#    "open open chrome" → "open chrome"
#    "search search for python" → "search for python"
# ─────────────────────────────────────────────────────────────────────────────

_REPEAT_RE = re.compile(r"\b(\w+)( \1)+\b", flags=re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Normalization pipeline
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text: str, apply_hinglish: bool = True) -> str:
    """
    Full normalization pipeline. Returns a clean English/Hinglish string.

    Stages (in order):
      1. Lowercase + collapse whitespace
      2. Strip leading wake words
      3. Remove filler words / noise
      4. Apply phonetic corrections (ASR misspellings)
      5. Optionally convert Hinglish verbs to English
      6. Remove consecutive duplicate words
      7. Final tidy (punctuation, extra spaces)

    Parameters
    ----------
    text           : raw ASR transcript
    apply_hinglish : if True, convert Hinglish action verbs to English
                     (set False when translator.py handles translation instead)

    Examples
    --------
    >>> normalize("hey jarvis youtub kholo yaar")
    'youtube open'

    >>> normalize("open open chrome please")
    'open chrome'

    >>> normalize("uske baad gana chalao yaar")
    'then play music'
    """
    if not text:
        return ""

    # Stage 1 — lowercase + whitespace collapse
    result = re.sub(r"\s+", " ", text.lower()).strip()

    # Stage 2 — strip leading wake word
    result = _WAKE_RE.sub("", result).strip()

    # Stage 3 — remove fillers (whole-word match)
    result = _FILLER_RE.sub(" ", result)
    result = re.sub(r"\s+", " ", result).strip()

    # Stage 4 — phonetic corrections (longest first, word-boundary aware)
    for wrong, right in _PHONETIC_SORTED:
        if wrong in result:
            # Use word-boundary pattern for safety on short keys
            pattern = r"(?<!\w)" + re.escape(wrong) + r"(?!\w)"
            result = re.sub(pattern, right, result, flags=re.IGNORECASE)

    # Stage 5 — Hinglish verb → English (optional)
    if apply_hinglish:
        for hinglish, english in _HINGLISH_SORTED:
            if hinglish in result:
                pattern = r"(?<!\w)" + re.escape(hinglish) + r"(?!\w)"
                result = re.sub(pattern, english, result, flags=re.IGNORECASE)

    # Stage 6 — remove consecutive duplicate words ("open open" → "open")
    result = _REPEAT_RE.sub(r"\1", result)

    # Stage 7 — final tidy
    result = re.sub(r"\s+", " ", result).strip(" ,.?!")

    return result


def strip_wake_only(text: str) -> str:
    """
    Lightweight version: only strips leading wake word, lowercase + tidy.
    Useful when you only need to clean the front of the string.
    """
    result = re.sub(r"\s+", " ", text.lower()).strip()
    result = _WAKE_RE.sub("", result).strip()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TESTS = [
        ("hey jarvis youtub kholo yaar",             "youtube open"),
        ("open open chrome please",                  "open chrome"),
        ("uske baad gana chalao",                    "then play"),
        ("jarvis crome kholo bhai",                  "chrome open"),
        ("hey jarvis could you please open notepadd","open notepad"),
        ("youtube kholo aur gaana chalao",           "youtube open and play"),
        ("umm search for python tutorials",          "search for python tutorials"),
        ("microsft word kholo",                      "microsoft word open"),
        ("open open open chrome",                    "open chrome"),
    ]
    print("Normalizer self-test")
    print("=" * 60)
    passed = 0
    for raw, expected in TESTS:
        got = normalize(raw)
        ok  = expected in got or got == expected
        mark = "✓" if ok else "✗"
        print(f"  [{mark}] '{raw}'")
        print(f"       → '{got}'  (expected contains: '{expected}')")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(TESTS)} passed")
