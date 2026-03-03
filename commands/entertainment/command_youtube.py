"""
command_youtube.py  –  YouTube search helper
============================================
Uses a direct search URL so Jarvis always lands on the results page.
No pywhatkit dependency needed.

Public API
----------
    extract_youtube_topic(raw: str) -> str
        Strips filler words and returns the clean search topic.

    search_youtube(query: str) -> None
        Opens YouTube search results for 'query' in the default browser.
        If query is empty, opens the YouTube homepage.
"""

import re
import webbrowser
from urllib.parse import quote_plus

# ── Filler-word removal ──────────────────────────────────────────────────────
# Order matters: longer / more-specific phrases first to avoid partial matches.
_FILLER_PATTERNS = [
    # English – action phrases
    r"\bsearch\s+for\b",
    r"\bsearch\b",
    r"\bplay\b",
    r"\bopen\b",
    r"\bfind\b",
    r"\bshow\s+me\b",
    r"\bshow\b",
    r"\blook\s+up\b",
    r"\bwatch\b",
    r"\bput\s+on\b",
    r"\bstream\b",

    # English – prepositions / conjunctions
    r"\bon\s+youtube\b",
    r"\bin\s+youtube\b",
    r"\bfrom\s+youtube\b",
    r"\bvia\s+youtube\b",
    r"\busing\s+youtube\b",
    r"\byoutube\s+pe\b",      # Hinglish "pe" = "on"
    r"\byoutube\s+par\b",     # Hinglish "par" = "on"
    r"\byoutube\b",

    # English – polite filler
    r"\bplease\b",
    r"\bfor\s+me\b",
    r"\bkaro\b",              # Hindi: "do it"
    r"\bkar\b",               # Hindi: "do"
    r"\blaao\b",              # Hindi: "bring"
    r"\bchalaao\b",           # Hindi: "play/run"
    r"\bchalao\b",
    r"\bdikhao\b",            # Hindi: "show"
    r"\bdekho\b",
    r"\bdekhna\b",

    # Hindi connectors often wrapping the topic
    r"\bpe\b",                # "on"
    r"\bpar\b",               # "on"
    r"\bwali\b",
    r"\bwala\b",
    r"\bka\b",
    r"\bki\b",
    r"\bke\b",
    r"\bse\b",

    # Generic trailing/leading noise
    r"\bvideo\b",
    r"\bvideos\b",
]

# Compile once for efficiency
_FILLER_RE = re.compile(
    "|".join(_FILLER_PATTERNS),
    flags=re.IGNORECASE
)

# Remove extra whitespace / punctuation left after stripping
_CLEANUP_RE = re.compile(r"[,;.\-–—]+")


def extract_youtube_topic(raw: str) -> str:
    """
    Remove YouTube-related filler words from *raw* and return the
    clean search topic.

    Examples
    --------
    >>> extract_youtube_topic("search python tutorial on youtube")
    'python tutorial'
    >>> extract_youtube_topic("youtube par ai video search karo")
    'ai'
    >>> extract_youtube_topic("open youtube and search coding music")
    'coding music'
    >>> extract_youtube_topic("youtube")
    ''
    """
    topic = raw.lower().strip()

    # Remove "and" only when it immediately follows "youtube …" or precedes
    # "search/play …" so we don't strip "and" inside a genuine topic like
    # "rock and roll".
    topic = re.sub(r"\byoutube\s+and\b", "", topic, flags=re.IGNORECASE)
    topic = re.sub(r"\band\s+(search|play|find|open)\b", "", topic, flags=re.IGNORECASE)

    # Strip all known filler patterns
    topic = _FILLER_RE.sub("", topic)

    # Remove stray punctuation
    topic = _CLEANUP_RE.sub(" ", topic)

    # Collapse whitespace
    topic = " ".join(topic.split())

    return topic


def run(command_text: str) -> str:
    """Standardized entry point for youtube command."""
    topic = extract_youtube_topic(command_text)
    search_youtube(topic)
    if topic:
        return f"Opening YouTube and searching for {topic}."
    return "Opening YouTube homepage."

def search_youtube(query: str) -> None:
    """
    Open YouTube in the default browser.
    """
    query = query.strip()
    if query:
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    else:
        url = "https://www.youtube.com"
    webbrowser.open(url)
