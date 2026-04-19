import os
import time
import sys
from dotenv import load_dotenv

# Ensure we have the right path
sys.path.append(os.getcwd())

print("--- JARVIS SPEECH DIAGNOSTIC ---")
load_dotenv("ni.env")

try:
    from core.audio.voice_engine import SpeechEngine
    print("[1] SpeechEngine imported successfully.")
except Exception as e:
    print(f"[ERROR] Failed to import SpeechEngine: {e}")
    sys.exit(1)

print("[2] Initializing SpeechEngine...")
engine = SpeechEngine()

print("[3] Testing Speech (Non-blocking)...")
test_text = "Jarvis testing environment. 1 2 3."
engine.speak(test_text)
print(f"[4] speak() returned. Is speaking: {engine.is_speaking}")

print("[5] Waiting for audio to finish (max 10s)...")
start_wait = time.time()
while engine.is_speaking and (time.time() - start_wait < 10):
    time.sleep(0.5)
    print(".", end="", flush=True)

if engine.is_speaking:
    print("\n[TIMEOUT] Speech engine is still stuck in 'speaking' state.")
else:
    print("\n[SUCCESS] Speech engine finished.")

print("\n--- Diagnostic Complete ---")
