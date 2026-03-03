from core.audio.speech_input import listen
from core.audio.voice_engine import speak
from brain.brain import think
from ui.visual_ui import JarvisUI
import random

WAIT_LINES = [
    "One moment, checking that.",
    "Let me fetch that for you.",
    "Hold on, getting the latest info.",
    "Just a second, thinking about it."
]

def run_core_loop(ui: JarvisUI):
    """
    Main execution loop: Listen -> Think -> Speak with UI integration.
    """
    print("[Core] Jarvis worker started.")
    
    while True:
        # 1. Listen State
        ui.set_state("LISTENING")
        text = listen()
        
        if text:
            # 2. Think State
            ui.set_state("WAKE")
            ui.set_subtitle(f"Processing...")
            reply = think(text)
            
            # 3. Speak State
            ui.set_state("SPEAKING")
            ui.set_subtitle(reply)
            speak(reply)
            
            # 4. Back to Idle
            ui.clear_subtitle()
            ui.set_state("IDLE")
        else:
            # Silent or no input? Stay/Return to IDLE
            ui.set_state("IDLE")
