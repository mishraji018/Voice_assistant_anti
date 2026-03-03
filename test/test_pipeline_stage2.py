"""
_test_phase2.py – Phase 2 module unit tests
Run: python _test_phase2.py
No microphone, pyttsx3, tkinter, or internet required.
"""
import sys, types, time, os, py_compile

# ---- Force UTF-8 output on Windows -----------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---- Stub pyttsx3 ----------------------------------------------------------
_spoken = []

class _FakeVoice:
    def __init__(self, idx):
        self.id   = f"voice{idx}"
        self.name = f"Voice{idx}"

class _FakeEngine:
    def say(self, t):            _spoken.append(t)
    def runAndWait(self):        pass
    def setProperty(self, k, v): pass
    def getProperty(self, k):
        if k == "voices":
            return [_FakeVoice(0), _FakeVoice(1)]
        return None

pyttsx3_mod = types.ModuleType("pyttsx3")
pyttsx3_mod.init = lambda: _FakeEngine()
sys.modules["pyttsx3"] = pyttsx3_mod


# ---- Stub speech_recognition -----------------------------------------------
class _FakeRecognizer:
    pause_threshold  = 1.0
    energy_threshold = 300

    def __init__(self):
        self.calls = 0

    def adjust_for_ambient_noise(self, *a, **k): pass

    def listen(self, *a, **k):
        self.calls += 1
        return f"audio{self.calls}"

    def recognize_google(self, audio, *a, **k):
        # First call returns valid phrase, later simulate noise
        if self.calls == 1:
            return "jarvis"
        raise _UnknownValueError()

class _UnknownValueError(Exception): pass
class _RequestError(Exception):      pass
class _WaitTimeout(Exception):       pass

class _FakeMic:
    def __enter__(self): return self
    def __exit__(self, *a): pass

sr_mod = types.ModuleType("speech_recognition")
sr_mod.Recognizer       = _FakeRecognizer
sr_mod.Microphone       = _FakeMic
sr_mod.UnknownValueError = _UnknownValueError
sr_mod.RequestError     = _RequestError
sr_mod.WaitTimeoutError = _WaitTimeout
sys.modules["speech_recognition"] = sr_mod


# ---- Stub tkinter -----------------------------------------------------------
tk_mod = types.ModuleType("tkinter")

class _Canvas:
    def pack(self, **k): pass
    def create_text(self, *a, **k): return 0
    def create_oval(self, *a, **k): return 0
    def create_rectangle(self, *a, **k): return 0
    def create_line(self, *a, **k): return 0
    def delete(self, *a): pass
    def itemconfig(self, *a, **k): pass

class _StringVar:
    def set(self, v): pass
    def get(self): return ""

class _Tk:
    def title(self, *a): pass
    def configure(self, **k): pass
    def resizable(self, *a): pass
    def attributes(self, *a): pass
    def mainloop(self): pass
    def after(self, *a): pass
    def destroy(self): pass

tk_mod.Tk        = _Tk
tk_mod.Canvas    = _Canvas
tk_mod.StringVar = _StringVar
sys.modules["tkinter"] = tk_mod


# =============================================================================
print("=" * 60)
print(" JARVIS PHASE 2 - UNIT TESTS")
print("=" * 60)


# ---- 1. connectivity_checker ------------------------------------------------
print("\n[1] CONNECTIVITY CHECKER")

from connectivity_checker import needs_internet, connectivity_status

cases = [
    ("SEARCH_WEB","",True),
    ("NEWS","",True),
    ("INFO_QUERY","weather",True),
    ("INFO_QUERY","time",False),
    ("OPEN_APP","chrome",False),
]

ok_count = 0
for intent, entity, expected in cases:
    r = needs_internet(intent, entity)
    ok = r == expected
    ok_count += ok
    print(f"  {'PASS' if ok else 'FAIL'}: {intent}/{entity} -> {r}")

print("  Connectivity:", connectivity_status())
print(f"  Result: {ok_count}/{len(cases)} passed")


# ---- 2. response_manager ----------------------------------------------------
print("\n[2] RESPONSE MANAGER")

from response_manager import ResponseManager
rm = ResponseManager()

_spoken.clear()
rm.pre_action("OPEN_APP","Chrome")
rm.post_action("OPEN_APP","Chrome")

print("  Example responses:", _spoken)


# ---- 3. wake_word_listener --------------------------------------------------
print("\n[3] WAKE WORD LISTENER")

from wake_word_listener import WakeWordListener
ww = WakeWordListener(speak_fn=lambda t: _spoken.append(t))

tests = [("hey jarvis",True),("jarvis",True),("play music",False)]
passed = 0

for text, exp in tests:
    r = ww._is_wake_word(text)
    ok = r == exp
    passed += ok
    print(f"  {'PASS' if ok else 'FAIL'}: '{text}' -> {r}")

ww.start_active_timer(0.05)
time.sleep(0.1)
print("  Timer expired:", ww.is_timed_out())
ww.beat()
print("  Timer reset:", not ww.is_timed_out())


# ---- 4. visual_ui syntax check ----------------------------------------------
print("\n[4] VISUAL UI")

ui_path = os.path.join(os.path.dirname(__file__), "visual_ui.py")

try:
    py_compile.compile(ui_path, doraise=True)
    print("  PASS: visual_ui.py compiles")
except Exception as e:
    print("  FAIL:", e)


print("\n" + "=" * 60)
print(" ALL PHASE 2 CHECKS COMPLETE")
print("=" * 60)