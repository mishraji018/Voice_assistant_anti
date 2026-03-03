"""
_test_modules.py  –  Standalone unit tests for new Jarvis modules
Run: python _test_modules.py
Does NOT require microphone, pyttsx3, or internet.
"""
import sys, types

# ── Stub pyttsx3 (no hardware needed) ─────────────────────────────────────
pyttsx3_mod = types.ModuleType('pyttsx3')
_dummy_engine = type('E', (), {
    'say'        : lambda s, t: None,
    'runAndWait' : lambda s: None,
    'setProperty': lambda s, k, v: None,
})()
pyttsx3_mod.init = lambda: _dummy_engine
sys.modules['pyttsx3'] = pyttsx3_mod

# ── Stub speech_recognition ───────────────────────────────────────────────
sr_mod = types.ModuleType('speech_recognition')
sr_mod.Recognizer = object
sr_mod.Microphone = object
sr_mod.UnknownValueError = Exception
sr_mod.RequestError = Exception
sys.modules['speech_recognition'] = sr_mod

# ── Now safe to import new modules ────────────────────────────────────────
from brain.intent_engine import detect_intent
from core.infra.translator import translate_to_english
from response_engine import confirm, error_response, greet, task_done

print("=" * 55)
print("  JARVIS MULTILINGUAL MODULE – UNIT TESTS")
print("=" * 55)

# ── INTENT ENGINE ─────────────────────────────────────────────────────────
print("\n[1] INTENT ENGINE TESTS")
cases = [
    # (utterance,                              expected_intent)
    ("chrome kholo",                           "OPEN_APP"),
    ("open chrome",                            "OPEN_APP"),
    ("start chrome",                           "OPEN_APP"),
    ("launch browser",                         "OPEN_APP"),
    ("kya time ho raha hai",                   "INFO_QUERY"),
    ("aaj ka weather batao",                   "INFO_QUERY"),
    ("mujhe python seekhna hai search karo",   "SEARCH_WEB"),
    ("search for python tutorial",             "SEARCH_WEB"),
    ("screen band karo",                       "CLOSE_WINDOW"),
    ("ye website close karo",                  "CLOSE_WINDOW"),
    ("close window",                           "CLOSE_WINDOW"),
    ("play music",                             "MEDIA_CONTROL"),
    ("gaana bajao",                            "MEDIA_CONTROL"),
    ("shutdown",                               "SYSTEM_CONTROL"),
    ("wifi on karo",                           "SYSTEM_CONTROL"),
    ("take screenshot",                        "SYSTEM_CONTROL"),
    ("news batao",                             "NEWS"),
    ("headlines",                              "NEWS"),
    ("how are you",                            "SMALL_TALK"),
    ("kya haal hai",                           "SMALL_TALK"),
    ("hello jarvis",                           "SMALL_TALK"),
    ("set reminder buy milk",                  "NOTE_TASK"),
    ("add task send report",                   "NOTE_TASK"),
    ("calculate 5 plus 3",                     "CALCULATOR"),
    ("today date",                             "INFO_QUERY"),
    ("volume up",                              "SYSTEM_CONTROL"),
]

passed = failed = 0
for text, expected in cases:
    r = detect_intent(text)
    ok = r["intent"] == expected
    passed += ok
    failed += (not ok)
    status = "PASS" if ok else "FAIL"
    ent = f" | entity='{r['entity']}'" if r["entity"] else ""
    print(f"  {status}: \"{text}\"\n         -> {r['intent']} (want {expected}, conf={r['confidence']}){ent}")

print(f"\n  Result: {passed}/{len(cases)} PASSED")

# ── TRANSLATOR ────────────────────────────────────────────────────────────
print("\n[2] TRANSLATOR TESTS  (dict-based, offline)")
pairs = [
    ("chrome kholo",         "en"),
    ("screen band karo",     "en"),
    ("aaj ka weather batao", "en"),
    ("time batao",           "en"),
    ("search karo python",   "en"),
    ("gaana bajao",          "en"),
    ("mujhe python chahiye", "en"),
    ("band karo",            "en"),
    ("shuru karo notepad",   "en"),
]
for src, lang in pairs:
    out = translate_to_english(src, lang)
    print(f"  \"{src}\"")
    print(f"   -> \"{out}\"")

# ── RESPONSE ENGINE ───────────────────────────────────────────────────────
print("\n[3] RESPONSE ENGINE TESTS")
print("  Randomness check (4 calls each, expect >=2 unique):")
for intent in ["OPEN_APP", "SEARCH_WEB", "INFO_QUERY",
               "CLOSE_WINDOW", "NEWS", "SYSTEM_CONTROL", "SMALL_TALK"]:
    ent = "Chrome" if intent == "OPEN_APP" else ""
    phrases = [confirm(intent, ent) for _ in range(4)]
    n_unique = len(set(phrases))
    result = "PASS" if n_unique >= 2 else "WARN"
    print(f"  {result}: {intent} – {n_unique}/4 unique")
    print(f"    Sample: {phrases[0]}")

print("\n  Greetings:")
for h, label in [(9, "morning"), (14, "afternoon"), (19, "evening"), (23, "night")]:
    print(f"  {label:10s}: {greet(h)}")

print("\n  Error response  :", error_response())
print("  Task done (OPEN):", task_done("OPEN_APP", "Chrome"))
print("  Task done (SRCH):", task_done("SEARCH_WEB", "Python"))

print("\n" + "=" * 55)
print("  ALL CHECKS COMPLETE")
print("=" * 55)
