"""
voice_utils.py  –  Unified speech interface

IMPORTANT:
This file does NOT create any TTS engine.
It only forwards speech to ResponseManager.
"""

_rm = None


def set_response_manager(rm):
    """Register the global ResponseManager instance."""
    global _rm
    _rm = rm


def speak(text):
    if not text:
        return

    print("Jarvis:", text)

    if _rm:
        _rm.speak(text)