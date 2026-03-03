"""
speech_pipeline.py  –  Hindi-first speech recognition pipeline
==============================================================
PRIMARY:   Vosk offline Hindi model (fast, private, works without internet)
FALLBACK:  Google Speech API (online, higher accuracy, used when Vosk
           confidence is below threshold or model is unavailable)

Returns a dict:
    {
        "text"      : str,   # normalized English/transliterated text
        "lang"      : str,   # "hi-IN" | "en-IN"
        "confidence": float, # 0.0 – 1.0
        "source"    : str,   # "vosk" | "google" | "error"
    }

Usage
-----
    from speech_pipeline import SpeechPipeline

    mic   = SpeechPipeline()
    result = mic.listen()
    print(result["text"], result["confidence"])

Installation (Vosk Hindi model)
--------------------------------
    pip install vosk sounddevice numpy
    # Download model from https://alphacephei.com/vosk/models
    # Recommended: vosk-model-hi-0.22  (~1.5 GB, best accuracy)
    # Lightweight:  vosk-model-small-hi-0.22  (~42 MB)
    # Place the extracted folder at:
    #   Voice_Assistant/models/vosk-model-hi/
    # The pipeline auto-detects the path.
"""

import os
import re
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Tuple

import speech_recognition as sr

logger = logging.getLogger("SpeechPipeline")

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR   = Path(__file__).parent
_MODEL_DIRS = [
    _BASE_DIR / "models" / "vosk-model-hi",
    _BASE_DIR / "models" / "vosk-model-small-hi",
]
# Also scan for any other vosk Hindi model folders present
_models_dir = _BASE_DIR / "models"
if _models_dir.exists():
    _MODEL_DIRS += [p for p in _models_dir.glob("vosk-model*hi*") if p not in _MODEL_DIRS]

# ── Tuning constants ──────────────────────────────────────────────────────────
VOSK_CONFIDENCE_THRESHOLD = 0.55   # below this → use Google fallback
GOOGLE_LANGUAGE            = "hi-IN"  # prefer Hindi; fall back tries en-IN
LISTEN_TIMEOUT             = 5.0    # seconds to wait for speech start
PHRASE_TIME_LIMIT          = 10.0   # max clip length


# ─────────────────────────────────────────────────────────────────────────────
# Hindi → English intent keyword mapping
# ─────────────────────────────────────────────────────────────────────────────
HINDI_KEYWORD_MAP: dict[str, str] = {
    # Greetings
    "namaste"   : "hello",
    "namaskar"  : "hello",
    "alvida"    : "goodbye",
    "shukriya"  : "thank you",
    "dhanyavaad": "thank you",

    # Commands
    "kholo"     : "open",
    "band karo" : "close",
    "band"      : "close",
    "chalaao"   : "play",
    "chalao"    : "play",
    "bajao"     : "play",
    "roko"      : "stop",
    "rok do"    : "stop",
    "dhundho"   : "search",
    "dhundhe"   : "search",
    "dhoondho"  : "search",
    "karo"      : "do",
    "batao"     : "tell me",
    "dikhaao"   : "show",
    "dikhao"    : "show",
    "seedha"    : "directly",
    "sunao"     : "play",
    "suno"      : "listen",

    # Media / apps
    "youtube par": "on youtube",
    "youtube pe" : "on youtube",
    "gaana"      : "song",
    "gana"       : "song",
    "sangeet"    : "music",
    "video"      : "video",

    # Info queries
    "mausam"     : "weather",
    "mausam kaisa hai": "what is the weather",
    "samay"      : "time",
    "samay kya hai": "what is the time",
    "aaj ki taareekh": "today's date",
    "aaj ka din" : "today's date",

    # System
    "band karo"  : "shutdown",
    "restart karo": "restart",
    "volume badhao": "volume up",
    "volume kam karo": "volume down",
    "mute karo"  : "mute",

    # Misc
    "madat"      : "help",
    "theek hai"  : "okay",
    "haan"       : "yes",
    "nahi"       : "no",
}


def normalize_hindi(text: str) -> str:
    """
    Apply Hindi → English keyword substitutions and clean up the text.
    Longer phrases are matched first to prevent partial-match collisions.
    """
    text = text.lower().strip()
    # Sort by length descending so longer phrases are replaced first
    for hindi, english in sorted(HINDI_KEYWORD_MAP.items(), key=lambda x: -len(x[0])):
        text = re.sub(rf"\b{re.escape(hindi)}\b", english, text, flags=re.IGNORECASE)
    # Collapse extra whitespace
    return " ".join(text.split())


# ─────────────────────────────────────────────────────────────────────────────
# Vosk wrapper (lazy-loaded)
# ─────────────────────────────────────────────────────────────────────────────

class _VoskRecognizer:
    """Lazy singleton for the Vosk recognizer."""

    _model      = None
    _recognizer = None
    _available  = None   # None = untested, True/False after first call

    @classmethod
    def _find_model_path(cls):  # -> Optional[Path]
        for p in _MODEL_DIRS:
            if p.is_dir():
                return p
        return None

    @classmethod
    def load(cls) -> bool:
        """Try to load the Vosk model. Returns True on success."""
        if cls._available is not None:
            return cls._available
        try:
            from vosk import Model, KaldiRecognizer   # type: ignore
            model_path = cls._find_model_path()
            if model_path is None:
                logger.warning(
                    "[Vosk] No model found. Checked: %s",
                    [str(p) for p in _MODEL_DIRS]
                )
                cls._available = False
                return False
            logger.info("[Vosk] Loading model from %s …", model_path)
            cls._model      = Model(str(model_path))
            cls._available  = True
            logger.info("[Vosk] Model loaded successfully.")
        except ImportError:
            logger.warning("[Vosk] Package not installed (pip install vosk).")
            cls._available = False
        except Exception as exc:
            logger.warning("[Vosk] Load error: %s", exc)
            cls._available = False
        return cls._available

    @classmethod
    def transcribe(cls, audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """
        Transcribe raw PCM bytes.
        Returns {"text": str, "confidence": float}.
        """
        if not cls.load():
            return {"text": "", "confidence": 0.0}
        try:
            from vosk import KaldiRecognizer   # type: ignore
            rec = KaldiRecognizer(cls._model, sample_rate)
            rec.SetWords(True)   # enables per-word confidence
            rec.AcceptWaveform(audio_bytes)
            raw = json.loads(rec.FinalResult())
            text = raw.get("text", "").strip()
            # Estimate confidence from per-word scores when available
            words = raw.get("result", [])
            if words:
                conf = sum(w.get("conf", 0.0) for w in words) / len(words)
            else:
                conf = 0.8 if text else 0.0
            return {"text": text, "confidence": conf}
        except Exception as exc:
            logger.error("[Vosk] Transcription error: %s", exc)
            return {"text": "", "confidence": 0.0}


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline class
# ─────────────────────────────────────────────────────────────────────────────

class SpeechPipeline:
    """
    A drop-in replacement for the existing `listen()` function that:
    1. Opens the microphone once and keeps the stream alive.
    2. Tries Vosk offline Hindi recognition first.
    3. Falls back to Google if Vosk confidence < threshold.
    4. Normalizes Hindi keywords to English equivalents.
    5. Returns a structured result dict.
    """

    def __init__(
        self,
        vosk_threshold: float = VOSK_CONFIDENCE_THRESHOLD,
        listen_timeout: float = LISTEN_TIMEOUT,
        phrase_limit:   float = PHRASE_TIME_LIMIT,
    ):
        self._threshold      = vosk_threshold
        self._listen_timeout = listen_timeout
        self._phrase_limit   = phrase_limit

        # Cached SpeechRecognition recognizer (avoids re-init overhead)
        self._sr = sr.Recognizer()
        self._sr.pause_threshold          = 0.8
        self._sr.dynamic_energy_threshold = True
        self._sr.energy_threshold         = 300

        # Pre-load Vosk in background so first listen() isn't slow
        threading.Thread(target=_VoskRecognizer.load, daemon=True).start()

        self._vosk_available = False   # updated after first listen

    # ── Core listen ──────────────────────────────────────────────────────────

    def listen(self) -> dict:
        """
        Record one utterance and return a result dict:
            {"text": str, "lang": str, "confidence": float, "source": str}
        """
        audio_data, sample_rate = self._capture_audio()
        if audio_data is None:
            return {"text": "", "lang": "en-IN", "confidence": 0.0, "source": "error"}

        # ── PRIMARY: Vosk offline ─────────────────────────────────────────
        vosk_result = _VoskRecognizer.transcribe(audio_data, sample_rate)
        vosk_text   = vosk_result["text"]
        vosk_conf   = vosk_result["confidence"]

        logger.debug("[Pipeline] Vosk: %r  conf=%.2f", vosk_text, vosk_conf)

        if vosk_text and vosk_conf >= self._threshold:
            normalized = normalize_hindi(vosk_text)
            logger.info("[Pipeline] Vosk accepted: %r → %r", vosk_text, normalized)
            return {
                "text"      : normalized,
                "lang"      : "hi-IN",
                "confidence": vosk_conf,
                "source"    : "vosk",
            }

        # ── FALLBACK: Google ─────────────────────────────────────────────
        google_result = self._google_fallback(audio_data, sample_rate)
        return google_result

    # ── Audio capture ────────────────────────────────────────────────────────

    def _capture_audio(self):  # -> Tuple[Optional[bytes], int]
        """
        Open the microphone, calibrate for noise, and capture one phrase.
        Returns (raw PCM bytes, sample_rate) or (None, 16000) on failure.
        """
        try:
            with sr.Microphone(sample_rate=16000) as source:
                self._sr.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._sr.listen(
                    source,
                    timeout=self._listen_timeout,
                    phrase_time_limit=self._phrase_limit,
                )
            raw   = audio.get_raw_data(convert_rate=16000, convert_width=2)
            return raw, 16000
        except sr.WaitTimeoutError:
            logger.debug("[Pipeline] Listen timeout — no speech detected.")
            return None, 16000
        except Exception as exc:
            logger.warning("[Pipeline] Audio capture error: %s", exc)
            return None, 16000

    # ── Google fallback ──────────────────────────────────────────────────────

    def _google_fallback(self, audio_bytes: bytes, sample_rate: int) -> dict:
        """
        Try Google speech recognition with Hindi then English.
        Returns the result dict regardless of success.
        """
        # Reconstruct an AudioData object
        audio_data = sr.AudioData(audio_bytes, sample_rate, 2)

        # Try Hindi first, then English as a secondary fallback
        for lang, lang_label in [("hi-IN", "hi-IN"), ("en-IN", "en-IN")]:
            try:
                text = self._sr.recognize_google(audio_data, language=lang).strip()
                if text:
                    normalized = normalize_hindi(text)
                    conf = 0.8   # Google doesn't expose confidence; assume decent
                    logger.info("[Pipeline] Google (%s): %r → %r", lang, text, normalized)
                    return {
                        "text"      : normalized,
                        "lang"      : lang_label,
                        "confidence": conf,
                        "source"    : "google",
                    }
            except sr.UnknownValueError:
                continue
            except sr.RequestError as exc:
                logger.warning("[Pipeline] Google API error (%s): %s", lang, exc)
                break

        logger.debug("[Pipeline] No speech recognized by any engine.")
        return {"text": "", "lang": "en-IN", "confidence": 0.0, "source": "error"}


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton + convenience function (drop-in for speech_input.py)
# ─────────────────────────────────────────────────────────────────────────────
_pipeline = None  # type: Optional[SpeechPipeline]


def _get_pipeline():  # -> SpeechPipeline
    global _pipeline
    if _pipeline is None:
        _pipeline = SpeechPipeline()
    return _pipeline


def listen_hindi() -> dict:
    """
    Convenience wrapper — same signature as speech_input.listen().
    Drop-in replacement:
        from speech_pipeline import listen_hindi as listen
    """
    return _get_pipeline().listen()


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    print("Speak now…")
    result = listen_hindi()
    print(f"\nResult: {json.dumps(result, ensure_ascii=False, indent=2)}")
