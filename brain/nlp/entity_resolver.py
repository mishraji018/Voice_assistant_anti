"""
entity_resolver.py  –  Stage 3: Fuzzy Entity Resolution
========================================================
Maps a raw phrase (possibly misspelled or Hinglish) to a validated
entity from a whitelist registry using character-level similarity.

Public API
----------
    from entity_resolver import resolve_entity, REGISTRY

    result = resolve_entity("youtub", category="app")
    # → {"name": "youtube", "type": "app", "exec": "chrome", "url": "...", "score": 0.92}

    result = resolve_entity("crome", category="browser")
    # → {"name": "chrome", ...}
"""

from __future__ import annotations
import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Entity Registry
# Each entry: name (canonical), type, exec (Windows binary), url (optional)
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY: list[dict] = [
    # ── Browsers ─────────────────────────────────────────────────────────────
    {"name": "chrome",       "type": "browser", "exec": "chrome",    "url": ""},
    {"name": "firefox",      "type": "browser", "exec": "firefox",   "url": ""},
    {"name": "edge",         "type": "browser", "exec": "msedge",    "url": ""},
    {"name": "opera",        "type": "browser", "exec": "opera",     "url": ""},
    {"name": "brave",        "type": "browser", "exec": "brave",     "url": ""},

    # ── Websites ─────────────────────────────────────────────────────────────
    {"name": "youtube",      "type": "website", "exec": "chrome",    "url": "https://youtube.com"},
    {"name": "google",       "type": "website", "exec": "chrome",    "url": "https://google.com"},
    {"name": "gmail",        "type": "website", "exec": "chrome",    "url": "https://mail.google.com"},
    {"name": "google maps",  "type": "website", "exec": "chrome",    "url": "https://maps.google.com"},
    {"name": "whatsapp",     "type": "website", "exec": "chrome",    "url": "https://web.whatsapp.com"},
    {"name": "telegram web", "type": "website", "exec": "chrome",    "url": "https://web.telegram.org"},
    {"name": "netflix",      "type": "website", "exec": "chrome",    "url": "https://netflix.com"},
    {"name": "github",       "type": "website", "exec": "chrome",    "url": "https://github.com"},
    {"name": "stackoverflow","type": "website", "exec": "chrome",    "url": "https://stackoverflow.com"},
    {"name": "chatgpt",      "type": "website", "exec": "chrome",    "url": "https://chat.openai.com"},

    # ── System apps ──────────────────────────────────────────────────────────
    {"name": "notepad",      "type": "app",     "exec": "notepad",   "url": ""},
    {"name": "calculator",   "type": "app",     "exec": "calc",      "url": ""},
    {"name": "paint",        "type": "app",     "exec": "mspaint",   "url": ""},
    {"name": "explorer",     "type": "app",     "exec": "explorer",  "url": ""},
    {"name": "file explorer","type": "app",     "exec": "explorer",  "url": ""},
    {"name": "task manager", "type": "app",     "exec": "taskmgr",   "url": ""},
    {"name": "settings",     "type": "app",     "exec": "ms-settings:","url": ""},
    {"name": "camera",       "type": "app",     "exec": "microsoft.windows.camera:", "url": ""},

    # ── Microsoft Office ─────────────────────────────────────────────────────
    {"name": "word",         "type": "office",  "exec": "WINWORD",   "url": ""},
    {"name": "excel",        "type": "office",  "exec": "EXCEL",     "url": ""},
    {"name": "powerpoint",   "type": "office",  "exec": "POWERPNT",  "url": ""},

    # ── Dev tools ─────────────────────────────────────────────────────────────
    {"name": "vscode",       "type": "dev",     "exec": "code",      "url": ""},
    {"name": "pycharm",      "type": "dev",     "exec": "pycharm",   "url": ""},
    {"name": "terminal",     "type": "dev",     "exec": "cmd",       "url": ""},
    {"name": "cmd",          "type": "dev",     "exec": "cmd",       "url": ""},
    {"name": "powershell",   "type": "dev",     "exec": "powershell","url": ""},
    {"name": "git bash",     "type": "dev",     "exec": "git-bash",  "url": ""},

    # ── Media / Social ────────────────────────────────────────────────────────
    {"name": "spotify",      "type": "media",   "exec": "spotify",   "url": "https://open.spotify.com"},
    {"name": "vlc",          "type": "media",   "exec": "vlc",       "url": ""},
    {"name": "discord",      "type": "social",  "exec": "Discord",   "url": ""},
    {"name": "zoom",         "type": "social",  "exec": "zoom",      "url": ""},
    {"name": "skype",        "type": "social",  "exec": "skype",     "url": ""},
    {"name": "teams",        "type": "social",  "exec": "teams",     "url": ""},
    {"name": "telegram",     "type": "social",  "exec": "telegram",  "url": ""},
    {"name": "whatsapp desktop","type":"social", "exec": "whatsapp",  "url": ""},
]

# Build a fast name → entry lookup
_NAME_INDEX: dict[str, dict] = {e["name"]: e for e in REGISTRY}

# Fuzzy threshold: below this score, reject the match
MIN_SCORE = 0.60


# ─────────────────────────────────────────────────────────────────────────────
# Similarity scorers
# ─────────────────────────────────────────────────────────────────────────────

def _jaro_winkler(s1: str, s2: str) -> float:
    """
    Jaro-Winkler similarity (0.0–1.0).
    Pure Python, no dependencies. Used for phonetic fuzzy matching.
    """
    s1, s2 = s1.lower(), s2.lower()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if not len1 or not len2:
        return 0.0

    match_dist = max(len1, len2) // 2 - 1
    if match_dist < 0:
        match_dist = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_dist)
        end   = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = s2_matches[j] = True
            matches += 1
            break

    if not matches:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (matches / len1 + matches / len2 +
            (matches - transpositions / 2) / matches) / 3

    # Winkler bonus for common prefix (up to 4 chars)
    prefix = 0
    for i in range(min(len(s1), len(s2), 4)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + prefix * 0.1 * (1 - jaro)


def _token_overlap(query: str, candidate: str) -> float:
    """Token-level overlap score. Good for multi-word entities."""
    q_tokens = set(query.lower().split())
    c_tokens = set(candidate.lower().split())
    if not q_tokens or not c_tokens:
        return 0.0
    intersection = q_tokens & c_tokens
    return len(intersection) / max(len(q_tokens), len(c_tokens))


def _score(query: str, candidate: str) -> float:
    """Combined similarity: max of Jaro-Winkler and token overlap."""
    jw = _jaro_winkler(query, candidate)
    to = _token_overlap(query, candidate)
    return max(jw, to)


# ─────────────────────────────────────────────────────────────────────────────
# Main resolver
# ─────────────────────────────────────────────────────────────────────────────

def resolve_entity(
    raw_phrase: str,
    category: Optional[str] = None,
    min_score: float = MIN_SCORE,
) -> Optional[dict]:
    """
    Resolve a raw (possibly misspelled / Hinglish) phrase to a known entity.

    Parameters
    ----------
    raw_phrase : the phrase to match (e.g. "youtub", "microsft word")
    category   : optional filter — "app", "browser", "website", "media", etc.
    min_score  : minimum similarity threshold (0–1). Matches below this are rejected.

    Returns
    -------
    dict with keys: name, type, exec, url, score
    None if no match meets the threshold.

    Examples
    --------
    >>> resolve_entity("youtub")
    {'name': 'youtube', 'type': 'website', 'exec': 'chrome',
     'url': 'https://youtube.com', 'score': 0.97}

    >>> resolve_entity("crome", category="browser")
    {'name': 'chrome', 'type': 'browser', 'exec': 'chrome', 'url': '', 'score': 0.91}

    >>> resolve_entity("watsapp")
    {'name': 'whatsapp', 'type': 'website', ...}
    """
    if not raw_phrase:
        return None

    query = raw_phrase.lower().strip()

    # Exact match fast path
    if query in _NAME_INDEX:
        entry = _NAME_INDEX[query]
        if category is None or entry["type"] == category:
            return {**entry, "score": 1.0}

    # Fuzzy search
    best_score  = 0.0
    best_entry  = None

    candidates = REGISTRY if category is None else [
        e for e in REGISTRY if e["type"] == category
    ]

    for entry in candidates:
        s = _score(query, entry["name"])
        if s > best_score:
            best_score = s
            best_entry = entry

    if best_entry and best_score >= min_score:
        result = {**best_entry, "score": round(best_score, 3)}
        print(f"[EntityResolver] '{raw_phrase}' → '{result['name']}' (score={best_score:.2f})")
        return result

    print(f"[EntityResolver] No match for '{raw_phrase}' (best={best_score:.2f})")
    return None


def get_entry(canonical_name: str) -> Optional[dict]:
    """Direct lookup by exact canonical name."""
    return _NAME_INDEX.get(canonical_name.lower())


def all_names() -> list[str]:
    """Return all canonical entity names."""
    return list(_NAME_INDEX.keys())


# ─────────────────────────────────────────────────────────────────────────────
# CLI self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TESTS = [
        ("youtub",        None,      "youtube"),
        ("you tube",      None,      "youtube"),
        ("crome",         "browser", "chrome"),
        ("grome",         None,      "chrome"),
        ("watsapp",       None,      "whatsapp"),
        ("what sapp",     None,      "whatsapp"),
        ("microsft word", None,      "word"),
        ("spottify",      "media",   "spotify"),
        ("discrd",        None,      "discord"),
        ("vs code",       "dev",     "vscode"),
        ("notpad",        "app",     "notepad"),
        ("calclatr",      "app",     "calculator"),
    ]
    print("EntityResolver self-test")
    print("=" * 60)
    passed = 0
    for query, cat, expected in TESTS:
        result = resolve_entity(query, category=cat)
        got    = result["name"] if result else "None"
        ok     = got == expected
        mark   = "✓" if ok else "✗"
        print(f"  [{mark}] '{query}' (cat={cat}) → '{got}'  (expected '{expected}')")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(TESTS)} passed")
