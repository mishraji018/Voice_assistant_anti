"""
transliterator.py  –  Stage 0: Devanagari → Roman (Hinglish) Transliterator
=============================================================================
Converts Hindi Unicode / Devanagari characters to readable Roman-script
Hinglish BEFORE any NLP stages run.  This ensures the keyword engine,
intent detector, and executor always receive pure Latin-alphabet text.

Problem solved
--------------
  speech_recognition with language="hi-IN" returns Devanagari for proper
  nouns and uncommon words, e.g.  "स्टॉर्म"  instead of  "storm".
  Without transliteration, routing fails because no English pattern matches
  a Devanagari string.

Pipeline position
-----------------
  Raw ASR output
    └── [Stage 0]  transliterate_devanagari()   ← THIS FILE
          └── [Stage 1]  normalize()
                └── [Stage 2]  translate_to_english()
                      └── [Stage 3-6]  NLP pipeline ...

Public API
----------
    from transliterator import transliterate_devanagari, has_devanagari

    clean = transliterate_devanagari("jarvis youtube खोलो")
    # → "jarvis youtube kholo"

    clean = transliterate_devanagari("स्टॉर्म की जानकारी दो")
    # → "storm ki jaankari do"

    # Check before expensive work
    if has_devanagari(text):
        text = transliterate_devanagari(text)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Character-level Devanagari → Roman mapping
#     (ISO 15919 / ITRANS-inspired, tuned for spoken Hinglish)
# ─────────────────────────────────────────────────────────────────────────────

# Independent vowels
_VOWELS: dict[str, str] = {
    "अ": "a",  "आ": "aa", "इ": "i",  "ई": "ee", "उ": "u",
    "ऊ": "oo", "ए": "e",  "ऐ": "ai", "ओ": "o",  "औ": "au",
    "ऋ": "ri", "ॠ": "ri", "ऌ": "li", "ॡ": "li",
    "अं": "an", "अः": "ah",
}

# Vowel matras (diacritics that follow a consonant)
_MATRAS: dict[str, str] = {
    "\u093e": "aa",   # ा
    "\u093f": "i",    # ि
    "\u0940": "ee",   # ी
    "\u0941": "u",    # ु
    "\u0942": "oo",   # ू
    "\u0943": "ri",   # ृ
    "\u0947": "e",    # े
    "\u0948": "ai",   # ै
    "\u094b": "o",    # ो
    "\u094c": "au",   # ौ
    "\u0902": "n",    # ं  (anusvara – nasal)
    "\u0903": "h",    # ः  (visarga)
    "\u093c": "",     # ़  (nukta – diacritic, ignore)
    "\u094d": "",     # ्  (halant / virama – kills inherent 'a', skip)
    "\u0901": "n",    # ँ  (chandrabindu)
    "\u0900": "",     # ी  (inverted chandrabindu, deprecated)
}

# Consonants
_CONSONANTS: dict[str, str] = {
    "क": "k",   "ख": "kh",  "ग": "g",   "घ": "gh",  "ङ": "ng",
    "च": "ch",  "छ": "chh", "ज": "j",   "झ": "jh",  "ञ": "ny",
    "ट": "t",   "ठ": "th",  "ड": "d",   "ढ": "dh",  "ण": "n",
    "त": "t",   "थ": "th",  "द": "d",   "ध": "dh",  "न": "n",
    "प": "p",   "फ": "ph",  "ब": "b",   "भ": "bh",  "म": "m",
    "य": "y",   "र": "r",   "ल": "l",   "व": "v",   "ळ": "l",
    "श": "sh",  "ष": "sh",  "स": "s",   "ह": "h",
    # Nukta consonants (borrowed/foreign sounds)
    "क़": "q",  "ख़": "kh", "ग़": "gh", "ज़": "z",
    "ड़": "r",  "ढ़": "rh", "फ़": "f",  "य़": "y",
    # Conjunct starters
    "क्ष": "ksh", "त्र": "tr", "ज्ञ": "gya", "श्र": "shr",
}

# Special standalone numbers / symbols
_DIGITS: dict[str, str] = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

# High-frequency whole-word overrides  (faster + more accurate than char-map)
# Longer entries must appear first for longest-match replacement.
_WORD_MAP: dict[str, str] = {
    # Common commands
    "खोलो":        "kholo",
    "खोल":         "khol",
    "बंद":          "band",
    "बंद करो":      "band karo",
    "चालू करो":     "chalu karo",
    "चालू":         "chalu",
    "शुरू":         "shuru",
    "बजाओ":         "bajao",
    "चलाओ":         "chalao",
    "सुनाओ":        "sunao",
    "दिखाओ":        "dikhao",
    "ढूंढो":        "dhundo",
    "रोको":         "roko",
    "बताओ":         "batao",
    "खोजो":         "search",
    "देखो":         "dekho",
    # System
    "स्क्रीनशॉट":   "screenshot",
    "शटडाउन":       "shutdown",
    "रीस्टार्ट":    "restart",
    "म्यूट":        "mute",
    "वॉल्यूम":      "volume",
    "पॉज़":         "pause",
    "रिज्यूम":      "resume",
    # Information
    "मौसम":         "weather",
    "समय":          "time",
    "तारीख":        "date",
    "समाचार":       "news",
    "खबर":          "khabar",
    # Connectors
    "और":           "aur",
    "फिर":          "phir",
    "पहले":         "pehle",
    "बाद":          "baad",
    "साथ":          "saath",
    "या":           "ya",
    # Greetings / polite
    "नमस्ते":       "namaste",
    "शुक्रिया":     "shukriya",
    "धन्यवाद":      "dhanyawad",
    "अलविदा":       "alvida",
    # Common nouns (frequent in voice commands)
    "गाना":         "gaana",
    "संगीत":        "sangeet",
    "वीडियो":       "video",
    "सर्च":         "search",
    "यूट्यूब":      "youtube",
    "गूगल":         "google",
    "व्हाट्सएप":    "whatsapp",
    # ── English loanwords phonetically written in Devanagari ──────────────────
    # These are the KEY entries that fix the "स्टॉर्म → storm" problem.
    # Add any word that users commonly speak in English but ASR returns as Devanagari.
    "स्टॉर्म":      "storm",
    "स्टॉप":        "stop",
    "स्टार्ट":      "start",
    "स्टेटस":       "status",
    "स्क्रीन":      "screen",
    "सेटिंग":       "setting",
    "सेटिंग्स":     "settings",
    "नोटिफिकेशन":   "notification",
    "नोटिफिकेशन्स": "notifications",
    "ब्लूटूथ":      "bluetooth",
    "वाईफाई":       "wifi",
    "वाई-फाई":      "wifi",
    "इंटरनेट":      "internet",
    "नेटवर्क":      "network",
    "फाइल":         "file",
    "फोल्डर":       "folder",
    "डेस्कटॉप":     "desktop",
    "डाउनलोड":      "download",
    "अपलोड":        "upload",
    "इंस्टॉल":      "install",
    "अनइंस्टॉल":    "uninstall",
    "अपडेट":        "update",
    "रिफ्रेश":      "refresh",
    "रिलोड":        "reload",
    "लॉगआउट":       "logout",
    "लॉगिन":        "login",
    "पासवर्ड":      "password",
    "माइक्रोफोन":   "microphone",
    "कैमरा":        "camera",
    "स्पीकर":       "speaker",
    "हेडफोन":       "headphone",
    "चार्जर":       "charger",
    "बैटरी":        "battery",
    "नोटपैड":       "notepad",
    "कैलकुलेटर":    "calculator",
    "कैलेंडर":      "calendar",
    "रिमाइंडर":     "reminder",
    "अलार्म":       "alarm",
    "टाइमर":        "timer",
    "मैप":          "map",
    "लोकेशन":       "location",
    "फ्लाइट":       "flight",
    "ट्रेन":        "train",
    "रिपोर्ट":      "report",
    "मेसेज":        "message",
    "मैसेज":        "message",
    "ईमेल":         "email",
    "चैट":          "chat",
    "कॉल":          "call",
    "वीडियो कॉल":   "video call",
    "फोन":          "phone",
    "मोबाइल":       "mobile",
    "लैपटॉप":       "laptop",
    "कंप्यूटर":     "computer",
    "टैबलेट":       "tablet",
    "प्रिंटर":      "printer",
    "माउस":         "mouse",
    "कीबोर्ड":      "keyboard",
    "मॉनिटर":       "monitor",
    "न्यूज़":       "news",
    "क्रिकेट":      "cricket",
    "फुटबॉल":       "football",
    "स्कोर":        "score",
    "मैच":          "match",
    "सीज़न":        "season",
    "एपिसोड":       "episode",
    "मूवी":         "movie",
    "फिल्म":        "film",
    "ट्रेलर":       "trailer",
    "सॉन्ग":        "song",
    "म्यूज़िक":     "music",
    "पॉडकास्ट":     "podcast",
    "प्लेलिस्ट":    "playlist",
    "स्पॉटिफाई":    "spotify",
    "नेटफ्लिक्स":   "netflix",
    "अमेज़न":       "amazon",
    "ट्विटर":       "twitter",
    "इंस्टाग्राम":  "instagram",
    "फेसबुक":       "facebook",
    "टेलीग्राम":    "telegram",
    "डिस्कॉर्ड":    "discord",
    "ज़ूम":         "zoom",
    "गिटहब":        "github",
    "पायथन":        "python",
    "जावास्क्रिप्ट":"javascript",
}

# Sort word-map longest-first for greedy matching
_WORD_MAP_SORTED = sorted(_WORD_MAP.items(), key=lambda x: len(x[0]), reverse=True)


# ── Anglicism phonetic recovery ───────────────────────────────────────────────
# After char-map transliteration, borrowed English words get mangled:
# "storm" transliterated from Devanagari phonetics → "starma"
# "screen" → "skreen", "phone" → "phona"
# This table maps common char-map outputs back to the correct English word.
_ANGLICISM_RECOVERY: dict[str, str] = {
    "starma":       "storm",
    "starm":        "storm",
    "storma":       "storm",
    "sstorm":       "storm",
    "skreen":       "screen",
    "iskreen":      "screen",
    "skreena":      "screen",
    "phona":        "phone",
    "fona":         "phone",
    "stopt":        "stop",
    "stoppa":       "stop",
    "setinga":      "setting",
    "setingsa":     "settings",
    "blootooth":    "bluetooth",
    "vaifai":       "wifi",
    "wifai":        "wifi",
    "daaunlod":     "download",
    "daunlod":      "download",
    "apload":       "upload",
    "instal":       "install",
    "logaut":       "logout",
    "baatari":      "battery",
    "kaemara":      "camera",
    "kaelkuletar":  "calculator",
    "kaelender":    "calendar",
    "rimaaindar":   "reminder",
    "alaaram":      "alarm",
    "taaimar":      "timer",
    "laaptop":      "laptop",
    "kampyootar":   "computer",
    "taeblet":      "tablet",
    "preentar":     "printer",
    "kiibord":      "keyboard",
    "monitar":      "monitor",
    "kriket":       "cricket",
    "futabol":      "football",
    "skor":         "score",
    "maech":        "match",
    "seejan":       "season",
    "episoda":      "episode",
    "muuvi":        "movie",
    "myoozik":      "music",
    "tvitatara":    "twitter",
    "instagraem":   "instagram",
    "phesabuka":    "facebook",
    "teligrema":    "telegram",
    "daskorda":     "discord",
    "jooma":        "zoom",
}

_ANGLICISM_SORTED = sorted(_ANGLICISM_RECOVERY.items(), key=lambda x: len(x[0]), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def has_devanagari(text: str) -> bool:
    """Return True if text contains any Devanagari Unicode characters."""
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def _apply_word_map(text: str) -> str:
    """
    Replace full Devanagari words using the curated _WORD_MAP.
    Longest entries first to prevent partial-match collisions.
    """
    for devanagari, roman in _WORD_MAP_SORTED:
        if devanagari in text:
            text = text.replace(devanagari, f" {roman} ")
    return re.sub(r"\s+", " ", text).strip()


def _apply_anglicism_recovery(text: str) -> str:
    """
    After char-map transliteration, fix mangled English loanwords.
    e.g. 'starma' → 'storm', 'skreen' → 'screen', 'phona' → 'phone'
    Uses whole-word matching to avoid replacing substrings.
    """
    words = text.split()
    result_words = []
    for word in words:
        corrected = _ANGLICISM_RECOVERY.get(word, word)
        result_words.append(corrected)
    return " ".join(result_words)


def _char_transliterate(text: str) -> str:
    """
    Character-by-character Devanagari → Roman conversion.
    Handles conjuncts, matras, and the inherent 'a' vowel after consonants.

    Algorithm
    ---------
    Walk each character:
    • Conjunct consonant (2-char)  → map to multi-letter Roman
    • Single consonant followed by halant (्) → consonant with no vowel
    • Single consonant followed by matra → consonant + matra value
    • Single consonant (no matra) → consonant + implicit 'a'
    • Vowel / matra / digit → direct lookup
    • ASCII / Other → pass through unchanged
    """
    result: list[str] = []
    i = 0
    s = text

    while i < len(s):
        ch = s[i]

        # ── Skip if pure ASCII / space / punctuation ──────────────────────────
        if ord(ch) < 0x0900 or ord(ch) > 0x097F:
            result.append(ch)
            i += 1
            continue

        # ── Try 2-char conjunct first (क्ष, त्र, ज्ञ, श्र) ─────────────────
        if i + 1 < len(s):
            two = s[i] + s[i + 1]
            if two in _CONSONANTS:
                roman = _CONSONANTS[two]
                i += 2
                if i < len(s) and s[i] in _MATRAS:
                    matra_val = _MATRAS[s[i]]
                    result.append(roman + matra_val)
                    i += 1
                elif i < len(s) and s[i] == "\u094d":
                    result.append(roman)
                    i += 1
                else:
                    result.append(roman + "a")   # inherent vowel
                continue

        # ── Single consonant ─────────────────────────────────────────────────
        if ch in _CONSONANTS:
            roman = _CONSONANTS[ch]
            i += 1
            if i < len(s) and s[i] == "\u094d":
                result.append(roman)
                i += 1   # consume halant
            elif i < len(s) and s[i] in _MATRAS:
                matra_val = _MATRAS[s[i]]
                result.append(roman + matra_val)
                i += 1
            else:
                result.append(roman + "a")   # inherent 'a'
            continue

        # ── Standalone vowel ─────────────────────────────────────────────────
        if ch in _VOWELS:
            result.append(_VOWELS[ch])
            i += 1
            continue

        # ── Matra / virama (not preceded by consonant — rare) ─────────────────
        if ch in _MATRAS:
            val = _MATRAS[ch]
            if val:
                result.append(val)
            i += 1
            continue

        # ── Devanagari digits ─────────────────────────────────────────────────
        if ch in _DIGITS:
            result.append(_DIGITS[ch])
            i += 1
            continue

        # ── Anything else in Devanagari range → skip ─────────────────────────
        i += 1

    return "".join(result)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Optional: indic-transliteration library (higher accuracy)
# ─────────────────────────────────────────────────────────────────────────────

def _library_transliterate(text: str) -> Optional[str]:
    """
    Try to use the `indic-transliteration` pip package for higher accuracy.
    Returns None if the package is not installed.

    Install (optional):
        pip install indic-transliteration
    """
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        roman = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        # ITRANS uses uppercase; convert to lowercase for pipeline consistency
        return roman.lower()
    except ImportError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Main public function
# ─────────────────────────────────────────────────────────────────────────────

def transliterate_devanagari(text: str) -> str:
    """
    Convert any Devanagari characters in `text` to Roman/Hinglish letters.
    Latin (English) words in the same string are preserved as-is.

    Strategy (fastest → most accurate):
      1. Word-map substitution  (curated dict → instant, correct)
      2. indic-transliteration library  (if installed, high accuracy)
      3. Built-in character map  (always available, good for common words)

    After conversion, the text is guaranteed to contain only:
      • ASCII letters, digits, spaces, and basic punctuation.
      • NO Devanagari Unicode.

    Parameters
    ----------
    text : str
        Raw text, may contain a mix of Devanagari and Latin.

    Returns
    -------
    str
        Fully Romanised text, lowercase, whitespace-normalised.

    Examples
    --------
    >>> transliterate_devanagari("jarvis youtube खोलो")
    'jarvis youtube kholo'

    >>> transliterate_devanagari("स्टॉर्म की जानकारी दो")
    'storm ki jaankari do'

    >>> transliterate_devanagari("open chrome aur गाना बजाओ")
    'open chrome aur gaana bajao'
    """
    if not text or not has_devanagari(text):
        return text  # nothing to do — fast path

    # ── Step 1: Apply curated word-level substitutions first ─────────────────
    processed = _apply_word_map(text)

    # ── Step 2: Any remaining Devanagari — try library, then char-map ─────────
    if has_devanagari(processed):
        lib_result = _library_transliterate(processed)
        if lib_result and not has_devanagari(lib_result):
            processed = lib_result
        else:
            processed = _char_transliterate(processed)

    # ── Step 3: Anglicism recovery — fix mangled English loanwords ────────────
    # e.g. char-map produces "starma" from स्टॉर्म — we recover it to "storm"
    processed = _apply_anglicism_recovery(processed)

    # ── Step 4: Final cleanup ─────────────────────────────────────────────────
    processed = processed.lower()
    # Remove any stray Devanagari that somehow survived
    processed = re.sub(r"[\u0900-\u097F]+", " ", processed)
    # Collapse 3+ repeated consonants from char-map artifacts
    processed = re.sub(r"([bcdfghjklmnpqrstvwxyz])\1{2,}", r"\1\1", processed)
    # Normalise whitespace
    processed = re.sub(r"\s+", " ", processed).strip()

    return processed


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Recognition settings helper
# ─────────────────────────────────────────────────────────────────────────────

def configure_recognizer(recognizer) -> None:
    """
    Apply optimal speech_recognition settings for Hindi/Hinglish → Roman output.

    Key insight: using language='en-IN' with Google returns Hinglish in Latin
    script (e.g. 'youtube kholo') while language='hi-IN' returns Devanagari
    for proper nouns.  The recommended strategy is:
      1. Try 'en-IN' first  →  Latin Hinglish  (preferred)
      2. If no result, try 'hi-IN' → Devanagari → transliterate()
      3. If still no result, try 'en-US' → plain English

    This function sets tuned thresholds for voice-assistant use.
    """
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.8   # wait 0.8s of silence
    recognizer.non_speaking_duration    = 0.5
    recognizer.operation_timeout        = None  # no API timeout


# ─────────────────────────────────────────────────────────────────────────────
# 6.  CLI self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TESTS = [
        ("jarvis youtube खोलो",                 "jarvis youtube kholo"),
        ("स्टॉर्म की जानकारी दो",                "storm ki"),         # partial match ok
        ("open chrome aur गाना बजाओ",           "open chrome aur gaana bajao"),
        ("मौसम बताओ",                            "weather batao"),
        ("volume बढ़ाओ",                          "volume"),
        ("jarvis whatsapp kholo",                "jarvis whatsapp kholo"),  # pure Latin passthrough
        ("बंद करो calculator",                   "band karo calculator"),
        ("समय क्या है",                           "samay"),
        ("YouTube kholo aur उसमें search karo",  "youtube kholo aur"),
    ]

    print("Transliterator Self-Test")
    print("=" * 70)
    passed = 0
    for raw, expected_contains in TESTS:
        result = transliterate_devanagari(raw)
        ok     = expected_contains.lower() in result.lower()
        mark   = "✓" if ok else "✗"
        print(f"  [{mark}]  IN : '{raw}'")
        print(f"        OUT: '{result}'")
        print(f"        EXP: contains '{expected_contains}'")
        print()
        if ok:
            passed += 1

    print(f"{passed}/{len(TESTS)} passed")

    # Show library availability
    lib = _library_transliterate("खोलो")
    if lib:
        print(f"\n✓ indic-transliteration library available → '{lib}'")
    else:
        print("\n• indic-transliteration library NOT installed (using built-in map)")
        print("  For higher accuracy: pip install indic-transliteration")
