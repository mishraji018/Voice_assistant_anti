import os
import random
from voice_utils import speak

def play_music():
    music_folder = "C:/Users/YourUsername/Music/"  # Change to your music folder path
    try:
        songs = [song for song in os.listdir(music_folder) if song.endswith((".mp3", ".wav"))]
        if songs:
            song_to_play = random.choice(songs)
            os.startfile(os.path.join(music_folder, song_to_play))
            speak(f"Playing {song_to_play}")
        else:
            speak("No music files found.")
    except Exception:
        speak("Failed to play music.")
