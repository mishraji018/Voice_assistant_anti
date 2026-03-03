"""
keyword_engine.py  –  Fast, keyword-first intent detection for Jarvis
======================================================================
Complements intent_engine.py by scanning for important trigger words
ANYWHERE in the sentence, making detection robust to natural phrasing:

    "please open chrome for me"       → OPEN_APP("chrome")
    "can you play some music"         → PLAY_MUSIC
    "gana chalao"                     → PLAY_MUSIC
    "chrome kholo"                    → OPEN_APP("chrome")
    "samay kya hai"                   → TIME_QUERY
    "aaj ki date"                     → DATE_QUERY
    "band karo chrome"                → CLOSE_WINDOW

Design
------
* Priority-ordered rule table: higher-priority rules are tried first.
* Returns the SAME dict shape as detect_intent() for drop-in compatibility.
* confidence=1.0 for exact phrase matches, 0.8 for keyword hits.
* Falls back to None (not UNKNOWN) so the caller can chain to intent_engine.

Public API
----------
    from keyword_engine import keyword_match

    result = keyword_match("please open chrome for me")
    if result:
        intent = result["intent"]   # "OPEN_APP"
        entity = result["entity"]   # "chrome"
"""

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Known application names  (used for entity extraction in OPEN_APP)
# ─────────────────────────────────────────────────────────────────────────────

APP_NAMES: list[str] = [
    # Browsers
    "chrome", "firefox", "edge", "opera", "brave",
    # Office
    "word", "excel", "powerpoint", "notepad", "wordpad",
    # Dev
    "vscode", "vs code", "visual studio code", "pycharm", "terminal",
    "cmd", "command prompt", "powershell", "git bash",
    # System
    "calculator", "calc", "paint", "explorer", "file explorer",
    "task manager", "control panel", "settings", "camera",
    # Media / Social
    "spotify", "vlc", "discord", "teams", "zoom", "skype",
    "whatsapp", "telegram", "netflix",
]

# Pre-compile a combined pattern for speed
_APP_RE = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in sorted(APP_NAMES, key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Rule table
# ─────────────────────────────────────────────────────────────────────────────
# Each rule: {
#   "intent"   : str
#   "entity"   : str | "__app__" | "__search__" | "__after__:<word>"
#   "phrases"  : list[str]   ← exact sub-string matches (confidence 1.0)
#   "keywords" : list[str]   ← ANY of these words present (confidence 0.8)
#   "priority" : int         ← lower = tried first
#   "blocklist": list[str]   ← sentence MUST NOT contain these (avoid false hits)
# }
#
# "__app__"       → extract nearest app name from the sentence
# "__search__"    → extract search query by stripping action words
# "__after__:X"  → take words appearing after keyword X
# ─────────────────────────────────────────────────────────────────────────────

RULES: list[dict] = [

    # ── YouTube (before generic PLAY_MUSIC so "youtube" is prioritised) ──────
    {
        "intent"  : "OPEN_YOUTUBE",
        "entity"  : "youtube",
        "priority": 10,
        "phrases" : ["open youtube", "youtube kholo", "youtube chalao",
                     "youtube open karo", "youtube chala do"],
        "keywords": ["youtube"],
        "blocklist": ["search", "play", "gana", "song", "music"],
    },

    # ── Play music on YouTube (has both "youtube" + play/music/song) ─────────
    {
        "intent"  : "YOUTUBE_MUSIC",
        "entity"  : "",
        "priority": 11,
        "phrases" : ["play on youtube", "youtube pe gana", "youtube pe music",
                     "play music on youtube", "play song on youtube",
                     "youtube pe sunao", "youtube par sunao",
                     "search youtube", "youtube par chalao"],
        "keywords": [],             # phrase-only rule
        "blocklist": [],
    },

    # ── OPEN_APP ─────────────────────────────────────────────────────────────
    {
        "intent"  : "OPEN_APP",
        "entity"  : "__app__",
        "priority": 20,
        "phrases" : [
            "open chrome", "open firefox", "open edge", "open notepad",
            "open calculator", "open word", "open excel", "open powerpoint",
            "open vscode", "open vs code", "open spotify", "open discord",
            "open vlc", "open whatsapp", "open telegram", "open zoom",
            "open skype", "open teams", "open paint", "open explorer",
            "open file explorer", "open task manager", "open camera",
            "open settings", "open cmd", "open terminal", "open powershell",
            "open brave", "open opera",
            # Hinglish
            "chrome kholo", "firefox kholo", "edge kholo", "notepad kholo",
            "calculator kholo", "spotify kholo", "discord kholo",
            "chrome chalao", "firefox chalao", "browser chalao",
            "chrome chalu karo", "browser kholo", "browser open karo",
        ],
        # NOTE: 'chalao' and 'sunao' intentionally excluded from keywords
        # because they're ambiguous (also mean play/sing in Hinglish).
        # Specific Hinglish app names are in phrases list above.
        "keywords": ["open", "launch", "start", "run",
                     "kholo", "chalu", "kholna"],
        "blocklist": [],
    },

    # ── PLAY_MUSIC ───────────────────────────────────────────────────────────
    {
        "intent"  : "PLAY_MUSIC",
        "entity"  : "",
        "priority": 30,
        "phrases" : [
            "play music", "play song", "play songs", "play a song",
            "play some music", "play me a song", "put on some music",
            "play something", "chalao music", "gana bajao", "gana chalao",
            "gana sunao", "gaana bajao", "gaana chalao", "gaana sunao",
            "music chalao", "music bajao", "music sunao",
            "song sunao", "song chalao", "koi gana sunao",
            "music play karo", "song play karo",
        ],
        "keywords": ["music", "song", "gana", "gaana", "bajao", "play"],
        # 'sunao' removed from keywords: too generic (news sunao, etc.)
        # 'news' blocklist prevents catching 'news sunao'
        "blocklist": ["youtube", "spotify", "search", "find", "news", "khabar", "samachar"],
    },

    # ── SEARCH_WEB ───────────────────────────────────────────────────────────
    {
        "intent"  : "SEARCH_WEB",
        "entity"  : "__search__",
        "priority": 40,
        "phrases" : [
            "search for", "search about", "google search", "google for",
            "search on google", "look up", "find on internet",
            "browse for", "dhundo", "dhoondo", "internet pe dhundo",
            "google karo", "google pe dhundo",
        ],
        "keywords": ["search", "google", "find", "browse",
                     "dhundo", "dhoondo", "lookup"],
        "blocklist": [],
    },

    # ── TIME_QUERY ───────────────────────────────────────────────────────────
    {
        "intent"  : "TIME_QUERY",
        "entity"  : "",
        "priority": 50,
        "phrases" : [
            "what time is it", "what is the time", "current time",
            "tell me the time", "time batao", "time kya hai",
            "kya time ho raha hai", "samay kya hai", "samay batao",
            "kitna baj raha hai",
        ],
        "keywords": ["time", "samay", "baje"],
        "blocklist": ["real", "screen", "limit"],
    },

    # ── DATE_QUERY ───────────────────────────────────────────────────────────
    {
        "intent"  : "DATE_QUERY",
        "entity"  : "",
        "priority": 51,
        "phrases" : [
            "what is the date", "today's date", "what day is it",
            "date batao", "aaj ka date", "aaj ki date",
            "aaj kya date hai", "kya date hai aaj",
        ],
        "keywords": ["date", "aaj", "day"],
        "blocklist": ["time", "samay"],
    },

    # ── WEATHER ──────────────────────────────────────────────────────────────
    {
        "intent"  : "WEATHER",
        "entity"  : "__after__:in",
        "priority": 52,
        "phrases" : [
            "what's the weather", "weather report", "weather forecast",
            "weather in", "weather of", "weather today",
            "mausam batao", "aaj ka mausam", "mausam kaisa hai",
            "temperature batao", "temperature in",
        ],
        "keywords": ["weather", "mausam", "temperature", "forecast"],
        "blocklist": [],
    },

    # ── CLOSE_WINDOW ─────────────────────────────────────────────────────────
    {
        "intent"  : "CLOSE_WINDOW",
        "entity"  : "__app__",
        "priority": 60,
        "phrases" : [
            "close window", "close this", "close tab", "close app",
            "close application", "shut this", "band karo", "band kar do",
            "screen band karo", "ye band karo", "band ho jao",
            "chrome band karo", "firefox band karo",
        ],
        "keywords": ["close", "band", "shut", "kill", "exit", "quit"],
        "blocklist": [],
    },

    # ── SYSTEM_CONTROL ───────────────────────────────────────────────────────
    {
        "intent"  : "SYSTEM_CONTROL",
        "entity"  : "__after__:volume",
        "priority": 70,
        "phrases" : [
            "shutdown", "shut down", "restart", "reboot",
            "lock screen", "lock computer", "screen lock",
            "wifi on", "wifi off", "turn on wifi", "turn off wifi",
            "bluetooth on", "bluetooth off",
            "volume up", "increase volume", "volume badhao",
            "volume down", "decrease volume", "volume kam karo",
            "mute", "unmute", "take screenshot", "screenshot lo",
            "system info",
        ],
        "keywords": ["shutdown", "restart", "reboot", "lock",
                     "wifi", "bluetooth", "volume", "mute", "screenshot"],
        "blocklist": [],
    },

    # ── NOTE / TASK / REMINDER ────────────────────────────────────────────────
    {
        "intent"  : "NOTE_TASK",
        "entity"  : "__search__",
        "priority": 80,
        "phrases" : [
            "take a note", "take note", "write a note", "note karo",
            "note likho", "remind me", "set a reminder", "set reminder",
            "add task", "add todo", "add to my todo", "yaad dilao",
            "note lelo", "kaam add karo", "task add karo",
        ],
        "keywords": ["note", "remind", "reminder", "task", "todo",
                     "remember", "schedule", "alarm"],
        "blocklist": [],
    },

    # ── NEWS ─────────────────────────────────────────────────────────────────
    {
        "intent"  : "NEWS",
        "entity"  : "",
        "priority": 90,
        "phrases" : [
            "latest news", "tell me the news", "get the news",
            "what's in the news", "headlines", "top stories",
            "news batao", "khabar batao", "samachar batao", "news sunao",
            "khabar sunao", "samachar sunao", "news suno",
        ],
        "keywords": ["news", "headline", "headlines", "samachar",
                     "khabar", "stories"],
        "blocklist": [],
    },

    # ── CALCULATOR ───────────────────────────────────────────────────────────
    {
        "intent"  : "CALCULATOR",
        "entity"  : "__search__",
        "priority": 95,
        "phrases" : [
            "calculate", "what is the result of", "compute",
            "solve", "how much is", "kitna hai", "multiply",
        ],
        "keywords": ["calculate", "plus", "minus", "multiply", "divide",
                     "percent", "square", "root", "sum", "equals"],
        "blocklist": [],
    },

    # ── SCREEN_READ (Vision) ─────────────────────────────────────────────────
    {
        "intent"  : "SCREEN_READ",
        "entity"  : "__search__",
        "priority": 100,
        "phrases" : [
            "read the screen", "read screen", "what's on the screen",
            "what is on screen", "tell me what you see", "describe the screen",
            "read what's on screen", "screen kya hai", "screen padho",
            "screen par kya hai", "screen dekho",
        ],
        "keywords": ["screen", "read screen", "describe screen"],
        "blocklist": [],
    },

    # ── CLICK_ELEMENT (Control) ──────────────────────────────────────────────
    {
        "intent"  : "CLICK_ELEMENT",
        "entity"  : "__search__",
        "priority": 101,
        "phrases" : [
            "click", "click on", "click the", "press the button",
            "click button", "click login", "click submit", "click ok",
            "par click karo", "click karo",
        ],
        "keywords": ["click"],
        "blocklist": [],
    },

    # ── RESEARCH (Internet Brain) ────────────────────────────────────────────
    {
        "intent"  : "RESEARCH",
        "entity"  : "__search__",
        "priority": 35,
        "phrases" : [
            "research", "summarise", "summarize", "tell me about",
            "explain", "what is", "who is", "find information about",
            "find info on", "look up and explain", "research karo",
            "batao kya hai", "explain karo",
        ],
        "keywords": ["research", "summarise", "summarize", "explain"],
        "blocklist": ["youtube", "music", "song", "gana"],
    },
]

# Pre-sort by priority once at import time
RULES.sort(key=lambda r: r["priority"])


# ─────────────────────────────────────────────────────────────────────────────
# Entity extractors
# ─────────────────────────────────────────────────────────────────────────────

# Words to strip before extracting a search query
_SEARCH_STRIP_RE = re.compile(
    r"\b(search for|search about|search|google for|google|find me|find|"
    r"look up|browse for|browse|dhundo|dhoondo|internet pe|internet|"
    r"tell me about|tell me|show me|show|"
    r"note karo|note likho|take a note|take note|write a note|"
    r"remind me to|remind me|set reminder for|set reminder|"
    r"add task|add todo|calculate|compute|solve|how much is|kitna hai|"
    r"please|kindly|quickly|right now|can you|could you|would you|"
    r"i want to|i want|jarvis|hey jarvis)\b",
    flags=re.IGNORECASE,
)


def _extract_app(text: str) -> str:
    """Find the first recognised app name in text."""
    m = _APP_RE.search(text)
    return m.group(1).lower() if m else ""


def _extract_search(text: str) -> str:
    """Strip action verbs to get the query/entity."""
    cleaned = _SEARCH_STRIP_RE.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.?!")
    return cleaned


def _extract_after(text: str, pivot_word: str) -> str:
    """Return words after `pivot_word` in text."""
    pattern = re.compile(r"\b" + re.escape(pivot_word) + r"\s+(\w[\w\s]*)", re.IGNORECASE)
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def _resolve_entity(raw_spec: str, text: str) -> str:
    """Resolve an entity spec string to an actual entity value."""
    if raw_spec == "__app__":
        return _extract_app(text)
    if raw_spec == "__search__":
        return _extract_search(text)
    if raw_spec.startswith("__after__:"):
        pivot = raw_spec.split(":", 1)[1]
        return _extract_after(text, pivot)
    return raw_spec   # literal entity (e.g. "youtube")


# ─────────────────────────────────────────────────────────────────────────────
# Normaliser
# ─────────────────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Lowercase, collapse whitespace, strip leading punctuation."""
    return re.sub(r"\s+", " ", text.lower()).strip(" ,.?!")


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def keyword_match(text: str) -> Optional[dict]:
    """
    Try to match text against the keyword rule table.

    Returns
    -------
    dict  {intent, entity, confidence, raw}   — same shape as detect_intent()
    None  — no rule matched; caller should fall through to intent_engine

    Examples
    --------
    >>> keyword_match("please open chrome for me")
    {'intent': 'OPEN_APP', 'entity': 'chrome', 'confidence': 0.8, 'raw': ...}

    >>> keyword_match("gana chalao")
    {'intent': 'PLAY_MUSIC', 'entity': '', 'confidence': 1.0, 'raw': ...}

    >>> keyword_match("samay kya hai")
    {'intent': 'TIME_QUERY', 'entity': '', 'confidence': 1.0, 'raw': ...}
    """
    if not text or not text.strip():
        return None

    norm = _norm(text)
    tokens = set(norm.split())

    for rule in RULES:
        intent    = rule["intent"]
        blocklist = rule.get("blocklist", [])
        phrases   = rule.get("phrases", [])
        keywords  = rule.get("keywords", [])

        # Blocklist check — skip rule if any blocked word is present
        if any(b in norm for b in blocklist):
            continue

        # ── Phase 1: Exact phrase match (confidence 1.0) ─────────────────────
        for phrase in phrases:
            if _norm(phrase) in norm:
                entity = _resolve_entity(rule["entity"], norm)
                print(f"[KeywordEngine] phrase '{phrase}' → {intent}/{entity!r}")
                return {
                    "intent"    : intent,
                    "entity"    : entity,
                    "confidence": 1.0,
                    "raw"       : norm,
                }

        # ── Phase 2: Keyword hit (any keyword present, confidence 0.8) ────────
        if keywords and any(kw in tokens for kw in keywords):
            entity = _resolve_entity(rule["entity"], norm)
            matched_kw = next(kw for kw in keywords if kw in tokens)
            print(f"[KeywordEngine] keyword '{matched_kw}' → {intent}/{entity!r}")
            return {
                "intent"    : intent,
                "entity"    : entity,
                "confidence": 0.8,
                "raw"       : norm,
            }

    return None   # no match — caller falls through to intent_engine


# ─────────────────────────────────────────────────────────────────────────────
# Intent → executor-compatible intent mapping
# (keyword_engine uses more granular intents; this maps them to executor intents)
# ─────────────────────────────────────────────────────────────────────────────

INTENT_MAP: dict[str, str] = {
    "OPEN_YOUTUBE"  : "OPEN_APP",
    "YOUTUBE_MUSIC" : "MEDIA_CONTROL",
    "PLAY_MUSIC"    : "MEDIA_CONTROL",
    "SEARCH_WEB"    : "SEARCH_WEB",
    "TIME_QUERY"    : "INFO_QUERY",
    "DATE_QUERY"    : "INFO_QUERY",
    "WEATHER"       : "INFO_QUERY",
    "CLOSE_WINDOW"  : "CLOSE_WINDOW",
    "SYSTEM_CONTROL": "SYSTEM_CONTROL",
    "NOTE_TASK"     : "NOTE_TASK",
    "NEWS"          : "NEWS",
    "CALCULATOR"    : "CALCULATOR",
    "OPEN_APP"      : "OPEN_APP",
    # New modules
    "SCREEN_READ"   : "SCREEN_READ",
    "CLICK_ELEMENT" : "CLICK_ELEMENT",
    "RESEARCH"      : "RESEARCH",
}


def normalise_intent(ke_result: dict) -> dict:
    """
    Convert a keyword_engine result to the executor-compatible intent dict.

    Maps granular keyword intents (TIME_QUERY, PLAY_MUSIC, YOUTUBE_MUSIC …)
    to the broader executor intents (INFO_QUERY, MEDIA_CONTROL, OPEN_APP …).

    The original keyword intent is preserved in result["ke_intent"] for use
    by execute_step() in command_planner.py which understands the finer intents.
    """
    original = ke_result["intent"]
    mapped   = INTENT_MAP.get(original, original)
    return {
        "intent"    : mapped,
        "ke_intent" : original,         # finer-grained intent preserved
        "entity"    : ke_result["entity"],
        "confidence": ke_result["confidence"],
        "raw"       : ke_result["raw"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo / self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TESTS = [
        # (input_text, expected_intent, expected_entity_contains)
        ("please open chrome for me",           "OPEN_APP",       "chrome"),
        ("can you play some music",              "PLAY_MUSIC",     ""),
        ("gana chalao",                          "PLAY_MUSIC",     ""),
        ("gaana bajao yaar",                     "PLAY_MUSIC",     ""),
        ("chrome kholo",                         "OPEN_APP",       "chrome"),
        ("bhai firefox chalao",                  "OPEN_APP",       "firefox"),
        ("search for python tutorials",          "SEARCH_WEB",     "python tutorials"),
        ("google machine learning",              "SEARCH_WEB",     "machine learning"),
        ("samay kya hai",                        "TIME_QUERY",     ""),
        ("what time is it",                      "TIME_QUERY",     ""),
        ("aaj ki date kya hai",                  "DATE_QUERY",     ""),
        ("mausam batao",                         "WEATHER",        ""),
        ("weather in delhi",                     "WEATHER",        ""),
        ("band karo chrome",                     "CLOSE_WINDOW",   ""),
        ("close this window",                    "CLOSE_WINDOW",   ""),
        ("volume up please",                     "SYSTEM_CONTROL", ""),
        ("take a screenshot",                    "SYSTEM_CONTROL", ""),
        ("remind me to call mom",                "NOTE_TASK",      ""),
        ("latest news sunao",                    "NEWS",           ""),
        ("open youtube",                         "OPEN_YOUTUBE",   "youtube"),
        ("play music on youtube",                "YOUTUBE_MUSIC",  ""),
        ("open chrome and search python",        "OPEN_APP",       "chrome"),
    ]

    passed = 0
    for text, exp_intent, exp_entity_contains in TESTS:
        result = keyword_match(text)
        if result is None:
            ok = False
            got = "None"
        else:
            ok = (result["intent"] == exp_intent and
                  exp_entity_contains.lower() in result["entity"].lower())
            got = f"{result['intent']}/{result['entity']!r}"

        status = "OK  " if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] '{text[:42]:<42}' → {got}")

    print(f"\n{passed}/{len(TESTS)} passed")
