"""
translator.py  –  Hindi / Hinglish → English translation layer
===============================================================
Works in three stages:
  0. Transliterate Devanagari → Roman  (transliterator.py, Stage 0 safety net)
  1. Token-level substitution from HINDI_DICT  (offline, fast, ~150 entries)
  2. Falls back to googletrans for anything the dict missed

Usage
-----
    from core.infra.translator import translate_to_english
    english = translate_to_english("chrome kholo", lang="en")  # → "open chrome"
    english = translate_to_english("आज का मौसम बताओ", lang="hi")  # → "today weather tell me"
    english = translate_to_english("स्टॉर्म", lang="hi")          # → "storm"
"""

import re

# ---------------------------------------------------------------------------
# Master dictionary  –  Hindi/Hinglish → English token substitutions
# Order matters: longer / more-specific phrases must come BEFORE single words.
# ---------------------------------------------------------------------------
HINDI_DICT: dict[str, str] = {
    # ── App control ──────────────────────────────────────────────────────────
    "kholo"             : "open",
    "khol do"           : "open",
    "khol"              : "open",
    "band karo"         : "close",
    "band kar"          : "close",
    "band"              : "close",
    "chalu karo"        : "start",
    "chalu kar"         : "start",
    "chalu"             : "start",
    "shuru karo"        : "launch",
    "shuru kar"         : "launch",
    "shuru"             : "launch",
    "bund karo"         : "close",

    # ── System ───────────────────────────────────────────────────────────────
    "band karo computer": "shutdown computer",
    "restart karo"      : "restart",
    "lock karo"         : "lock",
    "screenshot lo"     : "take screenshot",
    "screenshot lelo"   : "take screenshot",
    "volume badha do"   : "volume up",
    "volume kam karo"   : "volume down",
    "mute karo"         : "mute",

    # ── Search / browse ──────────────────────────────────────────────────────
    "search karo"       : "search",
    "dhundo"            : "search",
    "dhoondo"           : "search",
    "search kare"       : "search",
    "google karo"       : "google search",
    "google pe dhundo"  : "google search",

    # ── Information queries ──────────────────────────────────────────────────
    "kya time ho raha hai" : "what is the time",
    "kya time hai"         : "what time is it",
    "time batao"           : "tell time",
    "samay batao"          : "tell time",
    "aaj ka weather batao" : "today weather",
    "weather batao"        : "weather",
    "mausam batao"         : "weather",
    "aaj ki date"          : "today date",
    "date batao"           : "tell date",
    "news batao"           : "tell news",
    "khabar batao"         : "tell news",
    "samachar batao"       : "tell news",
    "stock batao"          : "stock price",

    # ── Media ────────────────────────────────────────────────────────────────
    "gaana bajao"       : "play music",
    "music bajao"       : "play music",
    "gaana band karo"   : "stop music",
    "music band karo"   : "stop music",
    "youtube pe dekho"  : "youtube",
    "youtube chalao"    : "youtube",

    # ── Notes / tasks ────────────────────────────────────────────────────────
    "yaad dilao"        : "remind me",
    "yaad dila do"      : "remind me",
    "reminder laga do"  : "set reminder",
    "note likho"        : "take note",
    "note lelo"         : "take note",
    "task add karo"     : "add task",
    "kaam add karo"     : "add task",
    "tasks dikhao"      : "show tasks",

    # ── Small talk ───────────────────────────────────────────────────────────
    "kya haal hai"      : "how are you",
    "kaise ho"          : "how are you",
    "theek ho"          : "are you okay",
    "shukriya"          : "thank you",
    "dhanyawad"         : "thank you",
    "alvida"            : "goodbye",
    "band ho jao"       : "exit",
    "ruk jao"           : "stop",

    # ── Media (extended) ─────────────────────────────────────────────────────
    "gaana chalao"      : "play music",
    "gaana chala do"    : "play music",
    "gaana chala"       : "play music",
    "song chalao"       : "play music",
    "song chala do"     : "play music",
    "chalao"            : "play",
    "chala do"          : "play",
    "chala"             : "play",
    "youtube kholo"     : "open youtube",
    "youtube khol do"   : "open youtube",
    "youtube pe search karo" : "youtube search",
    "youtube pe dhundo" : "youtube search",
    "isme search karo"  : "search in this",
    "video chalao"      : "play video",
    "next song"         : "next song",
    "agla gaana"        : "next song",
    "pause karo"        : "pause",
    "pause kar do"      : "pause",
    "resume karo"       : "resume",

    # ── Conjunctions / connectors (keep before single-word entries) ───────────
    "aur"               : "and",
    "phir"              : "then",
    "pehle"             : "first",
    "baad mein"         : "then",
    "uske baad"         : "after that",
    "saath mein"        : "also",

    # ── Grammar helpers (go last) ─────────────────────────────────────────────
    "mujhe"             : "i want",
    "seekhna hai"       : "learn",
    "dekhna hai"        : "watch",
    "sunna hai"         : "listen",
    "chahiye"           : "need",
    "karo"              : "do",
    "kare"              : "do",
    "batao"             : "tell me",
    "bata do"           : "tell me",
    "dikhao"            : "show me",
    "pe"                : "on",
    "ke baare mein"     : "about",
    "ke liye"           : "for",
    "hai"               : "",
    "kya"               : "what",
    "aaj"               : "today",
    "abhi"              : "now",
    "jaldi"             : "quickly",
    "please"            : "please",
    "screen pe"         : "on screen",
    "jo chal raha"      : "that is running",
    "ye"                : "this",
    "yeh"               : "this",
    "woh"               : "that",

    # ── Devanagari common words ──────────────────────────────────────────────
    "खोलो"              : "open",
    "बंद करो"           : "close",
    "चालू करो"          : "start",
    "आज का मौसम"        : "today weather",
    "समय बताओ"          : "tell time",
    "क्या टाइम है"      : "what time is it",
    "न्यूज़ बताओ"       : "tell news",
    "गाना बजाओ"         : "play music",
    "स्क्रीनशॉट लो"    : "take screenshot",
    "शट डाउन"           : "shutdown",
    "रीस्टार्ट"         : "restart",

    # ── App names (kept as-is or standardised) ───────────────────────────────
    "chrome"            : "chrome",
    "google chrome"     : "chrome",
    "notepad"           : "notepad",
    "calculator"        : "calculator",
    "word"              : "word",
    "excel"             : "excel",
    "powerpoint"        : "powerpoint",
    "vscode"            : "vscode",
    "vs code"           : "vscode",
    "file explorer"     : "explorer",
    "paint"             : "paint",
    "task manager"      : "task manager",
}


def _dict_translate(text: str) -> str:
    """
    Apply token-level substitution using HINDI_DICT.

    Uses word-boundary regex so short keys (e.g. 'pe' → 'on') do NOT
    accidentally match inside already-translated English words ('open').
    Sorts by key length descending so longer phrases are matched first.
    """
    result = text.strip().lower()

    for key in sorted(HINDI_DICT, key=len, reverse=True):
        value = HINDI_DICT[key]
        # Build a word-boundary pattern.
        # For Devanagari keys (no ASCII word chars), use a simple split-based
        # approach; for ASCII keys use \b boundaries.
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in key)
        if has_devanagari:
            # Devanagari: plain substring replacement is fine (no ASCII collision)
            result = result.replace(key, value)
        else:
            # ASCII / Hinglish: use \b word boundaries to avoid substring hits
            escaped = re.escape(key)
            # Use (?<!\w) / (?!\w) instead of \b so multi-word phrases
            # with spaces work correctly
            pattern = r'(?<!\w)' + escaped + r'(?!\w)'
            result = re.sub(pattern, value, result)

    # Tidy up double spaces left by empty replacements
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


def _googletrans_translate(text: str, src: str = 'hi') -> str:
    """
    Use googletrans as a fallback.  Returns original text on any error.
    Compatible with googletrans==4.0.0-rc1.
    """
    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(text, src=src, dest='en')
        return result.text.lower()
    except Exception:
        # Network unavailable or wrong version – just return what we got
        return text


def translate_to_english(text: str, lang: str = 'en') -> str:
    """
    Main entry point.  Always returns an English string with no Devanagari.

    Parameters
    ----------
    text : raw transcript from speech_input.listen()
    lang : 'hi' for Hindi/Devanagari, 'en' for English/Hinglish
    """
    if not text:
        return ""

    # Step 0 – Transliterate any residual Devanagari to Roman BEFORE dict lookup
    # This is a safety net in case speech_input.py let some Devanagari through.
    # e.g. "स्टॉर्म" → "storm", "खोलो" → "kholo" (then dict maps to "open")
    try:
        from transliterator import has_devanagari, transliterate_devanagari
        if has_devanagari(text):
            text = transliterate_devanagari(text)
            print(f"[Translator] Transliterated: '{text}'")
    except ImportError:
        pass   # transliterator.py not present — skip gracefully

    # Step 1 – dict substitution (works for Hinglish Roman keys)
    translated = _dict_translate(text)

    # Step 2 – if any Devanagari somehow still remains, try Google Translate API
    if any('\u0900' <= ch <= '\u097F' for ch in translated):
        translated = _googletrans_translate(translated, src='hi')

    print(f"[Translator] '{text}' → '{translated}'")
    return translated
