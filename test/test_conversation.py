"""
_test_convo.py  –  Verification for Conversational Intelligence Engine
========================================================================
Tests:
1. Evening greeting flow (Mocking time)
2. Language selection persistency
3. Multilingual responses
4. Learning Agent (Corrections)
"""

import sys
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules["speech_recognition"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["pyttsx3"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["pyaudio"] = MagicMock()

from conversation_memory import ConversationMemory
from personality_profile import PersonalityProfile
from dialogue_engine import DialogueEngine
import datetime
from unittest.mock import patch

def test_convo_engine():
    print("Conversational Intelligence Engine Verification")
    print("=" * 60)

    # 1. Memory & Language Selection
    mem = ConversationMemory()
    mem.clear_session()
    mem.forget("language") # Reset for test
    
    print("\n[1] Testing Language Selection Persistence")
    # Simulate first run selection
    mem.set_language("hi")
    if mem.get_language() == "hi":
        print("  [PASS] Set language to 'hi' successfully.")
    else:
        print(f"  [FAIL] Language is {mem.get_language()}")

    # 2. Personality & Multilingual
    print("\n[2] Testing Multilingual Responses")
    pers = PersonalityProfile()
    
    # Test English Confirmation
    mem.set_language("en")
    res_en = pers.format_response("I did that.", memory=mem, context="confirmation")
    print(f"  EN Confirmation: {res_en}")
    
    # Test Hindi Confirmation
    mem.set_language("hi")
    res_hi = pers.format_response("Maine kar diya.", memory=mem, context="confirmation")
    print(f"  HI Confirmation: {res_hi}")
    
    if "Thik hai" in res_hi or "Ho gaya" in res_hi or "ji" in res_hi:
        print("  [PASS] Hindi personality markers detected.")
    else:
        print("  [FAIL] Hindi markers missing.")

    # 3. Learning Agent (Corrections)
    print("\n[3] Testing Learning Agent (Mappings)")
    dialogue = DialogueEngine(mem, pers)
    
    # Learn a mapping
    mem.learn_mapping("open blue app", "OPEN_APP", "chrome")
    
    # Trigger dialogue response (it should acknowledge the mapping)
    mem.set_language("hi")
    res_learned = dialogue.respond("open blue app")
    print(f"  Learned Response: {res_learned}")
    
    if "samajh gayi" in res_learned:
        print("  [PASS] Dialogue engine acknowledged learned mapping.")
    else:
        print("  [FAIL] Learned mapping check failed.")

    # 4. Greeting Flow (Main logic simulation)
    print("\n[4] Testing Evening Greeting Trigger")
    from main import init_session
    class MockRM:
        def speak(self, text, use_female=False): print(f"  [JARVIS SPEAK] {text}")
    class MockUI:
        def set_state(self, state): pass
    
    # Force evening time (10 PM)
    with patch('datetime.datetime') as mock_date:
        mock_date.now.return_value = datetime.datetime(2026, 3, 2, 22, 0, 0)
        from main import _SESSION_INITIALIZED
        import main
        main._SESSION_INITIALIZED = False # reset
        print("  Simulating evening startup (10 PM)...")
        init_session(mem, MockRM(), MockUI())

if __name__ == "__main__":
    test_convo_engine()
