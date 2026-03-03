"""
_test_phase3.py  -  Phase 3 conversational brain tests
Run: python _test_phase3.py
No mic, no pyttsx3, no internet, no tkinter needed.
"""
import sys, types, os, json, tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- Stub pyttsx3 -----------------------------------------------------------
class _FakeVoice:
    def __init__(self, i): self.id = f"v{i}"; self.name = f"Voice{i}"

class _FakeEngine:
    def say(self, t): pass
    def runAndWait(self): pass
    def setProperty(self, k, v): pass
    def getProperty(self, k):
        return [_FakeVoice(0), _FakeVoice(1)] if k == "voices" else None

pyttsx3_mod = types.ModuleType("pyttsx3")
pyttsx3_mod.init = lambda: _FakeEngine()
sys.modules["pyttsx3"] = pyttsx3_mod

# ---- Stub speech_recognition ------------------------------------------------
class _SR:
    class Recognizer:
        pause_threshold = 1.0
        energy_threshold = 300
        def __init__(self): pass
        def adjust_for_ambient_noise(self, *a, **k): pass
        def listen(self, *a, **k): return None
        def recognize_google(self, *a, **k): raise Exception()
    class Microphone:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    UnknownValueError = Exception
    RequestError      = Exception
    WaitTimeoutError  = Exception

sys.modules["speech_recognition"] = _SR

# ---- Stub googletrans -------------------------------------------------------
class _FakeTrans:
    def translate(self, t, dest="en", src="auto"):
        return type("R", (), {"text": t})()

googletrans_mod = types.ModuleType("googletrans")
googletrans_mod.Translator = _FakeTrans
sys.modules["googletrans"] = googletrans_mod

# ---- Redirect memory file to temp dir --------------------------------------
import conversation_memory as _cm_module
_tmp_memory = os.path.join(tempfile.gettempdir(), "_jarvis_test_memory.json")
_cm_module.MEMORY_FILE = _tmp_memory
if os.path.exists(_tmp_memory):
    os.remove(_tmp_memory)

# =============================================================================
print("=" * 60)
print(" JARVIS PHASE 3  -  UNIT TESTS")
print("=" * 60)

# ---- 1. ConversationMemory --------------------------------------------------
print("\n[1] CONVERSATION MEMORY")
from conversation_memory import ConversationMemory

mem = ConversationMemory()

# remember / recall
mem.remember("user_name", "Prateek")
assert mem.recall("user_name") == "Prateek", "Recall failed"
print("  PASS: remember/recall user_name")

# Verify JSON written to disk
assert os.path.exists(_tmp_memory), "JSON file not created"
with open(_tmp_memory) as f:
    data = json.load(f)
assert data.get("user_name") == "Prateek", "JSON wrong"
print("  PASS: persistent JSON written correctly")

# log_turn + recent_turns
mem.log_turn("user",   "open chrome", "OPEN_APP")
mem.log_turn("jarvis", "Opening Chrome...", "OPEN_APP")
mem.log_turn("user",   "search for python", "SEARCH_WEB")
turns = mem.recent_turns(3)
assert len(turns) == 3, f"Expected 3 turns, got {len(turns)}"
print(f"  PASS: log_turn + recent_turns ({len(turns)} turns stored)")

# user_name property
assert mem.user_name == "Prateek", "user_name property failed"
print("  PASS: user_name property")

# answer_meta_query
q_name     = mem.answer_meta_query("what's my name")
q_asked    = mem.answer_meta_query("what did i ask you")
q_duration = mem.answer_meta_query("how long have we been talking")
q_none     = mem.answer_meta_query("open chrome")  # not a meta query

assert q_name    and "Prateek" in q_name,  f"Name query failed: {q_name}"
assert q_asked   and len(q_asked) > 5,     f"Asks query failed: {q_asked}"
assert q_duration and "minute" in q_duration.lower() or "second" in q_duration.lower() or "just" in q_duration.lower(), f"Duration query failed: {q_duration}"
assert q_none is None, f"Non-meta should return None, got: {q_none}"

print(f"  PASS: answer_meta_query")
print(f"    name     -> {q_name}")
print(f"    asked    -> {q_asked}")
print(f"    duration -> {q_duration}")

# ---- 2. PersonalityProfile --------------------------------------------------
print("\n[2] PERSONALITY PROFILE")
from personality_profile import PersonalityProfile

persona = PersonalityProfile(use_name_freq=0.0, wit_freq=0.0)  # deterministic

# format_response - short (no opener added)
r1 = persona.format_response("Thanks for that.", mem, context="confirmation")
assert r1, "Empty response"
assert r1[-1] in ".!?", f"Missing sentence ending: {r1}"
print(f"  PASS: format_response <- {r1!r}")

# get_opener - no two consecutive same openers
openers = [persona.get_opener("agreement") for _ in range(6)]
consecutive_same = any(openers[i] == openers[i+1] for i in range(len(openers)-1))
assert not consecutive_same, f"Repeated consecutive opener: {openers}"
print(f"  PASS: get_opener no-repeat  (6 openers: {openers[:3]}...)")

# empathise
e_tired  = persona.empathise("tired")
e_happy  = persona.empathise("happy")
e_unknwn = persona.empathise("unknown_emotion")
assert e_tired  and len(e_tired)  > 5
assert e_happy  and len(e_happy)  > 5
assert e_unknwn and len(e_unknwn) > 5
print(f"  PASS: empathise  tired={e_tired!r}")

# react_to_compliment / criticism
c = persona.react_to_compliment()
cr = persona.react_to_criticism()
assert len(c) > 5 and len(cr) > 5
print(f"  PASS: react_to_compliment/criticism")

# ---- 3. DialogueEngine ------------------------------------------------------
print("\n[3] DIALOGUE ENGINE")
from dialogue_engine import DialogueEngine

mem2 = ConversationMemory()
mem2.remember("user_name", "Prateek")
dlg = DialogueEngine(mem2, persona)

dialogue_tests = [
    ("my name is Rohan",       "Rohan"),          # name learning
    ("who are you",             "assistant"),     # identity
    ("what can you do",         "app"),            # capabilities
    ("how are you",             ""),               # greeting (any response ok)
    ("i'm feeling tired today", ""),               # emotion
    ("you're awesome",          ""),               # compliment
    ("you're useless",          ""),               # criticism
    ("tell me more",            ""),               # follow-up
    ("what did i ask you",      ""),               # meta memory
    ("goodnight",               ""),               # farewell
]

passed = 0
for text, must_contain in dialogue_tests:
    response = dlg.respond(text)
    ok = (len(response) > 5) and (not must_contain or must_contain.lower() in response.lower())
    passed += ok
    tag = "PASS" if ok else "FAIL"
    short = response[:70] + ("..." if len(response) > 70 else "")
    print(f"  {tag}: '{text[:35]}' -> {short!r}")

print(f"  Result: {passed}/{len(dialogue_tests)} PASSED")

# Verify name was learned
assert mem2.recall("user_name") == "Rohan", "Name learning via dialogue failed"
print("  PASS: name learned and persisted via dialogue")

# ---- 4. Router  (routing_logic) --------------------------------------------
print("\n[4] ROUTING LOGIC")
from routing_logic import Router

router = Router()

routing_tests = [
    # (text,                        expected_mode)
    ("open chrome",                  "COMMAND"),
    ("search for python tutorials",  "COMMAND"),
    ("what is the time",             "COMMAND"),
    ("shutdown",                     "COMMAND"),
    ("play music",                   "COMMAND"),
    ("set reminder buy milk",        "COMMAND"),
    ("calculate 5 plus 3",           "COMMAND"),
    ("latest news",                  "COMMAND"),
    # Conversations
    ("i'm feeling tired today",      "CONVERSATION"),
    ("who are you",                  "CONVERSATION"),
    ("what can you do",              "CONVERSATION"),
    ("what did i ask you",           "CONVERSATION"),
    ("you're awesome",               "CONVERSATION"),
    ("what's my name",               "CONVERSATION"),
    ("my name is Prateek",           "CONVERSATION"),
    ("goodnight",                    "CONVERSATION"),
    ("good morning",                 "CONVERSATION"),
    ("tell me more",                 "CONVERSATION"),
    ("what do you think",            "CONVERSATION"),
    ("thanks",                       "CONVERSATION"),
]

passed2 = failed2 = 0
for text, expected in routing_tests:
    result = router.route(text)
    ok = result["mode"] == expected
    passed2 += ok; failed2 += (not ok)
    mark = "PASS" if ok else "FAIL"
    print(f"  {mark}: {text!r:40s} -> {result['mode']} (want {expected})")

print(f"  Result: {passed2}/{len(routing_tests)} PASSED")

# ---- Summary ----------------------------------------------------------------
print("\n" + "=" * 60)
total = len(dialogue_tests) + len(routing_tests) + 8  # +8 memory/persona
total_pass = passed + passed2 + 8
print(f" PHASE 3 COMPLETE: {total_pass}/{total} checks passed")
print("=" * 60)

# Cleanup
if os.path.exists(_tmp_memory):
    os.remove(_tmp_memory)
