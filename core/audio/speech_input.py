"""
speech_input.py  –  Robust multilingual speech recognizer for Jarvis
====================================================================
✔ Works with Hindi + Hinglish + English
✔ Prefers en-IN recognition → returns Latin Hinglish  (e.g. "youtube kholo")
✔ Automatically transliterates Devanagari to Roman if hi-IN fires first
✔ Has timeout protection (never freezes Jarvis)
✔ Noise-filtered listening
✔ Fresh sr.Recognizer() each call (never reuses stale state)
✔ Multi-utterance buffering: waits for follow-up phrases (like Alexa)
✔ Always returns a safe dict: {"raw": str, "lang": "hi"|"en"}

Recognition language preference order
--------------------------------------
  1. 'en-IN'  →  returns Latin-script Hinglish  (PREFERRED — no Devanagari)
  2. 'hi-IN'  →  returns Devanagari Unicode      (FALLBACK — then transliterated)
  3. 'en-US'  →  plain English                   (LAST RESORT)
"""

import time
import speech_recognition as sr

# Stage-0 transliteration: Devanagari → Roman (NEW)
try:
    from brain.nlp.transliterator import transliterate_devanagari, has_devanagari, configure_recognizer
except Exception:
    def transliterate_devanagari(text: str) -> str:
        return text

    def has_devanagari(text: str) -> bool:
        return any("\u0900" <= ch <= "\u097F" for ch in text)

    def configure_recognizer(recognizer) -> None:
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
# ──────────────────────────────────────────────────────────────
# Tunable constants
# ──────────────────────────────────────────────────────────────
_LISTEN_TIMEOUT          = 6      # seconds to wait for speech to START
_PHRASE_LIMIT            = 8      # max seconds of a single phrase
_BUFFER_WINDOW           = 2.5    # seconds to wait for a follow-up phrase
_BUFFER_FOLLOW_TIMEOUT   = 1.5   # shorter timeout for follow-up segments
_AMBIENT_DURATION        = 0.3    # calibrate noise this many seconds


def _is_hindi_unicode(text: str) -> bool:
    """Detect real Hindi / Devanagari characters."""
    return has_devanagari(text)


# ──────────────────────────────────────────────────────────────
# Core: single listen attempt
# ──────────────────────────────────────────────────────────────

def listen_once(timeout: float = _LISTEN_TIMEOUT,
                phrase_limit: float = _PHRASE_LIMIT) -> dict:
    """
    One listen attempt. Always returns {"raw": str, "lang": "hi"|"en"}.
    Creates a brand-new sr.Recognizer() every call — no stale state.
    Opens a fresh sr.Microphone() context — no stream conflicts.
    Never raises; all exceptions return empty string.

    IMPORTANT — recognition order
    -----------------------------
    We try 'en-IN' FIRST.  Google's en-IN model outputs Hinglish commands in
    Roman script (e.g. "youtube kholo", "gaana bajao") so the NLP pipeline
    receives clean Latin text without any Devanagari.

    We only fall back to 'hi-IN' if en-IN returns nothing.  When hi-IN fires,
    any Devanagari characters are immediately transliterated to Roman via
    transliterator.transliterate_devanagari().
    """
    # ── Fresh recognizer every call ───────────────────────────────────────────
    recognizer = sr.Recognizer()
    configure_recognizer(recognizer)   # applies tuned thresholds

    try:
        with sr.Microphone() as source:
            # Calibrate on fresh stream each time
            recognizer.adjust_for_ambient_noise(source, duration=_AMBIENT_DURATION)
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit,
            )
    except sr.WaitTimeoutError:
        return {"raw": "", "lang": "en"}
    except OSError as e:
        print(f"[Mic Error] Stream conflict: {e}")
        return {"raw": "", "lang": "en"}
    except Exception as e:
        print(f"[Mic Error] {e}")
        return {"raw": "", "lang": "en"}

    # ── Priority 1: English-India (returns Latin Hinglish) ───────────────────
    # This is the PREFERRED path — outputs "youtube kholo", "gaana bajao" etc.
    # in Roman script with no Devanagari, so the NLP pipeline works directly.
    try:
        en_in_text = recognizer.recognize_google(audio, language="en-IN").strip()
        if en_in_text:
            print(f"[en-IN got]: {en_in_text}")
            # Sanity-check: if somehow en-IN returned Devanagari, transliterate
            if _is_hindi_unicode(en_in_text):
                en_in_text = transliterate_devanagari(en_in_text)
                print(f"[Transliterated]: {en_in_text}")
            return {"raw": en_in_text.lower(), "lang": "en"}
    except sr.UnknownValueError:
        pass   # no speech detected for en-IN, try hi-IN
    except sr.RequestError:
        pass   # network error — fall through to hi-IN

    # ── Priority 2: Hindi-India (returns Devanagari) → transliterate ─────────
    # Only reached when en-IN returns nothing (e.g. user spoke pure Hindi).
    # We immediately convert any Devanagari to Roman so the pipeline is clean.
    try:
        hi_text = recognizer.recognize_google(audio, language="hi-IN").strip()
        if hi_text:
            print(f"[hi-IN got]: {hi_text}")
            # Always transliterate, even if it's already Hinglish Roman
            if _is_hindi_unicode(hi_text):
                hi_roman = transliterate_devanagari(hi_text)
                print(f"[Transliterated]: {hi_roman}")
                return {"raw": hi_roman, "lang": "en"}   # return as 'en' — it's Latin now
            else:
                # hi-IN returned Roman (Hinglish) — use directly
                return {"raw": hi_text.lower(), "lang": "en"}
    except sr.UnknownValueError:
        pass
    except sr.RequestError:
        pass

    # ── Priority 3: US English last resort ───────────────────────────────────
    try:
        en_us_text = recognizer.recognize_google(audio, language="en-US").strip().lower()
        if en_us_text:
            print(f"[en-US got]: {en_us_text}")
            return {"raw": en_us_text, "lang": "en"}
    except sr.UnknownValueError:
        return {"raw": "", "lang": "en"}
    except sr.RequestError:
        print("[Speech] API unavailable. Check internet connection.")
        return {"raw": "", "lang": "en"}

    return {"raw": "", "lang": "en"}


# ──────────────────────────────────────────────────────────────
# Multi-utterance buffer
# ──────────────────────────────────────────────────────────────

def listen_with_buffer(first_timeout: float = _LISTEN_TIMEOUT,
                       buffer_window: float = _BUFFER_WINDOW) -> dict:
    """
    Multi-utterance listen — waits up to `buffer_window` seconds after each
    phrase for a follow-up, joining all parts into one command string.

    Example flow:
        User: "open youtube"  →  [pause: 1.8s]  →  "and search for music"
        Returns: {"raw": "open youtube and search for music", "lang": "en"}

    If no first phrase is heard, returns {"raw": "", "lang": "en"} immediately.
    """
    print("\n[Jarvis] 🎙  Listening…")

    first = listen_once(timeout=first_timeout, phrase_limit=_PHRASE_LIMIT)
    if not first["raw"]:
        return {"raw": "", "lang": "en"}

    parts    = [first["raw"]]
    lang     = first["lang"]
    deadline = time.monotonic() + buffer_window

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        nxt = listen_once(
            timeout=min(remaining, _BUFFER_FOLLOW_TIMEOUT),
            phrase_limit=_PHRASE_LIMIT,
        )
        if nxt["raw"]:
            # Transliterate follow-up fragment too, just in case
            fragment = nxt["raw"]
            if _is_hindi_unicode(fragment):
                fragment = transliterate_devanagari(fragment)
            parts.append(fragment)
            deadline = time.monotonic() + buffer_window   # reset window

    combined = " ".join(parts).strip()
    print(f"[Buffer] Combined: '{combined}'")
    return {"raw": combined, "lang": lang}


# ──────────────────────────────────────────────────────────────
# Backward-compatible alias  (main.py calls listen())
# ──────────────────────────────────────────────────────────────

def listen() -> str:
    """
    Drop-in replacement for the original listen().
    Now uses listen_with_buffer() internally so multi-part commands work.
    Returns ONLY the Latin/Roman text string.
    """
    result = listen_with_buffer()
    return result["raw"]
