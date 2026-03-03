"""
_test_reasoning.py  –  Integration Test for LLM Reasoning Engine
================================================================
Verifies that the LLM/Stub returns correct JSON and that the
nlp_pipeline handles it correctly.
"""

from nlp_pipeline import NLPPipeline, get_pipeline
import json

def test_flow():
    # Mock speak functions
    def _speak_f(msg): print(f"  [TTS-F] {msg}")
    def _speak_j(msg): print(f"  [TTS-J] {msg}")

    pipe = NLPPipeline(speak_fn=_speak_f, speak_jarvis=_speak_j)

    TEST_CASES = [
        {
            "name": "Multi-intent",
            "input": "open youtube and search for python",
            "expect_steps": 2
        },
        {
            "name": "Clarification",
            "input": "jarvis suggest something",
            "expect_clarify": True
        },
        {
            "name": "Single app",
            "input": "chrome kholo",
            "expect_intent": "OPEN_APP"
        },
        {
            "name": "Hindi Translit + Intent",
            "input": "\u092f\u0942\u091f\u094d\u092f\u0942\u092c \u0916\u094b\u0932\u094b", # यूट्यूब खोलो
            "expect_intent": "OPEN_URL" # upgraded from OPEN_APP for youtube
        }
    ]

    print("Reasoning Engine Integration Test")
    print("=" * 60)

    for case in TEST_CASES:
        print(f"\nTEST: {case['name']}")
        print(f"  Input: '{case['input']}'")
        
        result = pipe.process(case['input'])
        
        # Verify clarification
        if case.get("expect_clarify"):
            if result.needs_clarification:
                print(f"  [PASS] Correctly requested clarification: '{result.clarification_question}'")
            else:
                print(f"  [FAIL] Did not request clarification")
            continue

        # Verify steps
        if "expect_steps" in case:
            if len(result.steps) == case["expect_steps"]:
                print(f"  [PASS] Found correct number of steps: {len(result.steps)}")
            else:
                print(f"  [FAIL] Expected {case['expect_steps']} steps, got {len(result.steps)}")
        
        # Verify intent (for single handled or fallback)
        if "expect_intent" in case:
            actual_intent = ""
            if result.steps:
                actual_intent = result.steps[0].intent
            elif result.intent_result:
                actual_intent = result.intent_result["intent"]
            
            if actual_intent == case["expect_intent"]:
                print(f"  [PASS] Correct intent: {actual_intent}")
            else:
                print(f"  [FAIL] Expected intent {case['expect_intent']}, got {actual_intent}")

if __name__ == "__main__":
    test_flow()
