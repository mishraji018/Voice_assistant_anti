"""
command_music.py  –  Local music playback with YouTube Music fallback
======================================================================
• Tries to play a random local song from the user's Music folder.
• If the folder is empty, missing, or playback fails → opens YouTube Music.
• Never calls speak() directly — returns (success: bool, message: str).

Usage
-----
    from commands.command_music import play_music

    ok, msg = play_music()
    # ok=True  → local file started     (msg: "Playing <song>")
    # ok=False → YouTube Music opened   (msg: "Opening YouTube Music…")
"""

import os
import random
import webbrowser

YOUTUBE_MUSIC_URL = "https://music.youtube.com"

# Try the standard Windows Music folder; also accept an optional override
# via the JARVIS_MUSIC_FOLDER environment variable.
_DEFAULT_MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")
MUSIC_FOLDER = os.environ.get("JARVIS_MUSIC_FOLDER", _DEFAULT_MUSIC_FOLDER)

_AUDIO_EXTS = (".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".wma")


def play_music() -> tuple[bool, str]:
    """
    Attempt local music playback, fall back to YouTube Music.

    Returns
    -------
    (True,  "Playing <song_name>")            – local file launched
    (False, "Opening YouTube Music for you.") – fallback triggered
    """
    try:
        if not os.path.isdir(MUSIC_FOLDER):
            return _youtube_fallback("Music folder not found.")

        songs = [
            f for f in os.listdir(MUSIC_FOLDER)
            if f.lower().endswith(_AUDIO_EXTS)
        ]

        if not songs:
            return _youtube_fallback("No music files found in Music folder.")

        chosen = random.choice(songs)
        full_path = os.path.join(MUSIC_FOLDER, chosen)
        os.startfile(full_path)          # Windows-native: opens in default player
        song_name = os.path.splitext(chosen)[0]
        return True, f"Playing {song_name}."

    except Exception as exc:
        return _youtube_fallback(f"Playback error: {exc}")


def _youtube_fallback(reason: str) -> tuple[bool, str]:
    """Open YouTube Music in the browser and report why."""
    print(f"[MusicPlayer] Fallback triggered — {reason}")
    try:
        webbrowser.open(YOUTUBE_MUSIC_URL)
    except Exception:
        pass
    return False, "I couldn't play local music, so I've opened YouTube Music for you."
