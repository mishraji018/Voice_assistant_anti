"""
command_planner.py  –  Multi-step command parser & executor for Jarvis
=======================================================================
Splits a single sentence into ordered action steps and executes each one
sequentially.  Fully compatible with the existing execute() pipeline.

Supports English, Hindi & Hinglish connectors out of the box.

Now features context memory so that "on that / us par / wahan" references
are automatically resolved to the last opened application.

Public API
----------
    from commands.command_planner import CommandPlanner

    planner = CommandPlanner(speak_female=rm.speak,
                             speak_jarvis=lambda t: rm.speak(t, use_female=False))

    # Multi-step:
    handled = planner.try_multi("open youtube and play a song on that")
    # Returns True if 2+ steps were found and executed.

    # Single command with context reference:
    handled = planner.try_context("play song on that")
    # Returns True if a contextual reference was resolved and executed.

Architecture
------------
    1. split_steps()              – tokenise sentence on logical connectors
    2. parse_step()               – map each segment to (intent, entity)
    3. plan()                     – build ordered list of Step objects
    4. run_plan() / try_multi()   – execute each Step, narrate, recover on failure
    5. ContextMemory              – track last_app and resolve "on that" refs
"""

import re
import time
import webbrowser
import subprocess
import os
from dataclasses import dataclass, field
from typing import Callable

from brain.memory.context_memory import ContextMemory, ctx_mem

# ─────────────────────────────────────────────────────────────────────────────
# Step connectors (English + Hindi/Hinglish)
# ─────────────────────────────────────────────────────────────────────────────

# These words signal a boundary between two separate actions.
# Order matters: longer phrases must come before their substrings.
CONNECTORS = [
    r"\band then\b",
    r"\bthen\b",
    r"\band also\b",
    r"\balso\b",
    r"\band\b",
    r"\baur phir\b",       # Hinglish: "and then"
    r"\bphir\b",           # Hindi: "then"
    r"\baur\b",            # Hindi/Hinglish: "and"
    r"\bfir\b",            # Informal Hindi: "then"
    r"\biske baad\b",      # Hindi: "after this"
    r"\buske baad\b",      # Hindi: "after that"
]

_CONNECTOR_RE = re.compile(
    "|".join(CONNECTORS),
    flags=re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Keyword → (intent, entity_template) table
#
# Rules are tried IN ORDER; first match wins.
# Entity extraction is done separately by extract_entity().
# ─────────────────────────────────────────────────────────────────────────────

INTENT_RULES: list[dict] = [
    # ── Browser / App opens ──────────────────────────────────────────────────
    {"kw": ["open youtube",  "youtube kholo", "youtube chalao"],
     "intent": "OPEN_APP",  "entity": "youtube",  "url": "https://youtube.com"},
    {"kw": ["open chrome",   "chrome kholo",  "chrome chalao"],
     "intent": "OPEN_APP",  "entity": "chrome"},
    {"kw": ["open firefox",  "firefox kholo"],
     "intent": "OPEN_APP",  "entity": "firefox"},
    {"kw": ["open edge",     "edge kholo"],
     "intent": "OPEN_APP",  "entity": "edge"},
    {"kw": ["open gmail",    "gmail kholo",   "check mail", "open mail"],
     "intent": "OPEN_URL",  "entity": "Gmail",
     "url": "https://mail.google.com"},
    {"kw": ["open google",   "google kholo"],
     "intent": "OPEN_URL",  "entity": "Google",
     "url": "https://google.com"},
    {"kw": ["open maps",     "open google maps", "maps kholo"],
     "intent": "OPEN_URL",  "entity": "Google Maps",
     "url": "https://maps.google.com"},
    {"kw": ["open notepad",  "notepad kholo"],
     "intent": "OPEN_APP",  "entity": "notepad"},
    {"kw": ["open calculator","calculator kholo"],
     "intent": "OPEN_APP",  "entity": "calculator"},
    {"kw": ["open word",     "word kholo"],
     "intent": "OPEN_APP",  "entity": "word"},
    {"kw": ["open excel",    "excel kholo"],
     "intent": "OPEN_APP",  "entity": "excel"},
    {"kw": ["open vscode",   "open vs code", "vscode kholo"],
     "intent": "OPEN_APP",  "entity": "vscode"},
    {"kw": ["open spotify",  "spotify kholo"],
     "intent": "OPEN_APP",  "entity": "spotify"},
    {"kw": ["open discord",  "discord kholo"],
     "intent": "OPEN_APP",  "entity": "discord"},
    {"kw": ["open whatsapp", "whatsapp kholo"],
     "intent": "OPEN_URL",  "entity": "WhatsApp Web",
     "url": "https://web.whatsapp.com"},
    # ── Web search (before generic open, to avoid OPEN_APP stealing "search")─
    {"kw": ["search for", "search about", "google for", "look up",
            "find me", "search", "dhundo", "khojo", "find"],
     "intent": "SEARCH_WEB", "entity": "__extract__"},

    # ── YouTube ──────────────────────────────────────────────────────────────
    {"kw": ["play on youtube", "search youtube", "youtube par dhundo",
            "youtube mein search", "youtube par search",
            "play song on youtube", "play music on youtube",
            "play a song on youtube", "play songs on youtube"],
     "intent": "YOUTUBE_SEARCH", "entity": ""},
    # PLAY_MUSIC must come BEFORE generic 'chalao/kholo' rule
    {"kw": ["play music", "gana chalao", "gana sunao", "music chalao",
            "music play", "play song", "play a song", "play songs",
            "play some music", "gaana chalao", "gaana sunao"],
     "intent": "PLAY_MUSIC",   "entity": ""},

    # Generic "open <app>" — matched LAST (catches remaining 'open X')
    {"kw": ["open "],
     "intent": "OPEN_APP",  "entity": "__extract__"},

    # ── Weather / time / date info ───────────────────────────────────────────
    {"kw": ["what's the weather", "weather in", "weather of",
            "mausam batao", "weather check", "temperature"],
     "intent": "WEATHER",      "entity": "__extract__"},
    {"kw": ["what's the time", "current time", "time batao", "time kya hai"],
     "intent": "TIME",         "entity": ""},
    {"kw": ["what's the date", "today's date", "date batao", "aaj kya date hai"],
     "intent": "DATE",         "entity": ""},

    # ── System controls ──────────────────────────────────────────────────────
    {"kw": ["volume up",   "volume badhao"],
     "intent": "SYSTEM_CONTROL", "entity": "volume up"},
    {"kw": ["volume down", "volume kam karo"],
     "intent": "SYSTEM_CONTROL", "entity": "volume down"},
    {"kw": ["mute"],
     "intent": "SYSTEM_CONTROL", "entity": "mute"},
    {"kw": ["take screenshot", "screenshot lo", "screenshot lao"],
     "intent": "SYSTEM_CONTROL", "entity": "screenshot"},
    {"kw": ["lock screen", "screen lock karo"],
     "intent": "SYSTEM_CONTROL", "entity": "lock"},

    # ── Notes / todos ────────────────────────────────────────────────────────
    {"kw": ["add to my todo", "add task", "add todo"],
     "intent": "NOTE_TASK",    "entity": "__extract__"},
    {"kw": ["take a note", "write a note", "note karo", "note likho"],
     "intent": "NOTE_TASK",    "entity": "__extract__"},
    {"kw": ["set a reminder", "remind me", "set reminder"],
     "intent": "NOTE_TASK",    "entity": "__extract__"},

    # ── News / jokes ─────────────────────────────────────────────────────────
    {"kw": ["latest news", "news sunao", "kya news hai", "tell me news"],
     "intent": "NEWS",         "entity": ""},
    {"kw": ["tell me a joke", "joke sunao", "crack a joke"],
     "intent": "SMALL_TALK",   "entity": "joke"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Filler words removed before entity extraction
# ─────────────────────────────────────────────────────────────────────────────

FILLER_WORDS = [
    # English
    "for me", "please", "kindly", "quickly", "right now", "asap",
    "a ", "an ", "the ", "me ", "my ", "now",
    "could you", "can you", "would you", "i want to", "i want",
    "i need to", "i need", "i'd like to", "i'd like",
    "hey jarvis", "jarvis",
    # Hinglish
    "mujhe", "mere liye", "mera", "meri", "zara", "thoda",
    "please", "yaar", "bhai", "boss",
]

# Action-verb prefixes stripped to reveal the entity after keyword removal
ACTION_PREFIXES = [
    "open ", "search for ", "search about ", "search ",
    "find me ", "find ", "look up ", "google for ", "google ",
    "play on youtube ", "search youtube ", "play ",
    "check ", "tell me about ", "tell me ", "show me ", "show ",
    "remind me to ", "remind me ", "set reminder for ", "set reminder ",
    "add task ", "add todo ", "take note ", "write note ",
    "weather in ", "temperature in ", "weather of ",
    # Hinglish / Hindi
    "dhundo ", "khojo ", "gana chalao ", "gana sunao ", "sunao ",
    "batao ", "bolo ", "dikha ", "kholo ", "chalao ",
]


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Step:
    """One resolved action from the plan."""
    raw_segment : str
    intent      : str
    entity      : str
    meta        : dict = field(default_factory=dict)   # e.g. {"url": "..."}

    def __repr__(self):
        return f"Step({self.intent} | '{self.entity}' | raw='{self.raw_segment}')"


# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_entity(segment: str, matched_keywords: list[str]) -> str:
    """
    Remove action verbs, filler words, and keyword triggers from a segment
    to recover the meaningful entity (e.g. search topic, app name).

    Parameters
    ----------
    segment          : normalised segment string (lowercase)
    matched_keywords : list of keyword strings that triggered the intent rule

    Returns
    -------
    Cleaned entity string (may be empty).
    """
    text = segment.lower().strip()

    # 1. Remove the matched keyword trigger itself
    for kw in sorted(matched_keywords, key=len, reverse=True):
        text = text.replace(kw.lower(), " ", 1)

    # 2. Remove action prefixes
    for prefix in ACTION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    # 3. Remove filler words (exact match at word boundaries)
    for filler in sorted(FILLER_WORDS, key=len, reverse=True):
        text = re.sub(r"\b" + re.escape(filler.strip()) + r"\b", " ", text, flags=re.IGNORECASE)

    # 4. Tidy up
    text = re.sub(r"\s+", " ", text).strip(" ,.?!")
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Step splitter
# ─────────────────────────────────────────────────────────────────────────────

def split_steps(text: str) -> list[str]:
    """
    Split *text* into ordered segments on logical connectors.
    Empty segments and very short noise fragments (<= 2 chars) are discarded.

    Example
    -------
    >>> split_steps("open chrome and search a good book then play music")
    ['open chrome', 'search a good book', 'play music']
    """
    parts = _CONNECTOR_RE.split(text)
    return [p.strip() for p in parts if p and len(p.strip()) > 2]


# ─────────────────────────────────────────────────────────────────────────────
# Single-step resolver
# ─────────────────────────────────────────────────────────────────────────────

def parse_step(segment: str, ctx: ContextMemory | None = None) -> "Step | None":
    """
    Match a single segment against INTENT_RULES.

    If *ctx* is provided and the segment contains a contextual reference
    ("on that", "us par", …), the reference is resolved to ctx.last_app
    before matching.

    Returns a Step or None if no rule matched.
    """
    # Resolve contextual references first
    if ctx is not None and ctx.last_app and ctx.has_reference(segment):
        segment = ctx.resolve_reference(segment)

    norm = segment.lower().strip()

    for rule in INTENT_RULES:
        for kw in rule["kw"]:
            if kw.lower() in norm:
                raw_entity = rule.get("entity", "")
                if raw_entity == "__extract__":
                    entity = extract_entity(norm, [kw])
                else:
                    entity = raw_entity

                return Step(
                    raw_segment = segment,
                    intent      = rule["intent"],
                    entity      = entity,
                    meta        = {k: v for k, v in rule.items()
                                   if k not in ("kw", "intent", "entity")},
                )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Plan builder
# ─────────────────────────────────────────────────────────────────────────────

def plan(text: str, ctx: ContextMemory | None = None) -> list[Step]:
    """
    Parse full text into an ordered list of Steps (resolved actions).
    Unrecognised segments are skipped.

    Passes *ctx* into parse_step() so contextual references are resolved.

    Example
    -------
    >>> plan("open chrome and search a good book")
    [Step(OPEN_APP | 'chrome' | ...), Step(SEARCH_WEB | 'good book' | ...)]
    """
    segments = split_steps(text)
    steps    = []
    for seg in segments:
        step = parse_step(seg, ctx)
        if step:
            steps.append(step)
        else:
            print(f"[Planner] ⚠ No rule matched segment: '{seg}'")
    return steps


# ─────────────────────────────────────────────────────────────────────────────
# Step executor
# ─────────────────────────────────────────────────────────────────────────────

# App name → Windows executable (mirrors command_executor.APP_MAP)
_APP_MAP: dict[str, str] = {
    "chrome"        : "chrome",
    "google chrome" : "chrome",
    "firefox"       : "firefox",
    "edge"          : "msedge",
    "notepad"       : "notepad",
    "calculator"    : "calc",
    "word"          : "WINWORD",
    "excel"         : "EXCEL",
    "powerpoint"    : "POWERPNT",
    "vscode"        : "code",
    "vs code"       : "code",
    "paint"         : "mspaint",
    "explorer"      : "explorer",
    "file explorer" : "explorer",
    "task manager"  : "taskmgr",
    "spotify"       : "spotify",
    "vlc"           : "vlc",
    "discord"       : "Discord",
    "zoom"          : "zoom",
    "cmd"           : "cmd",
    "command prompt": "cmd",
    "powershell"    : "powershell",
}

import datetime as _dt

def execute_step(
    step        : Step,
    speak_fn    : Callable[[str], None],
    speak_jarvis: Callable[[str], None] | None = None,
    ctx         : ContextMemory | None = None,
) -> bool:
    """
    Execute a single Step.

    Parameters
    ----------
    step         : resolved Step object
    speak_fn     : female / pre-action voice (used for "Doing X…")
    speak_jarvis : Jarvis voice (used for confirmation).
                   Falls back to speak_fn if not provided.
    ctx          : ContextMemory instance — updated when an app is opened.

    Returns True on success, False on failure.
    """
    confirm = speak_jarvis or speak_fn
    intent  = step.intent
    entity  = step.entity
    meta    = step.meta

    try:
        # ── Open URL (fixed) ─────────────────────────────────────────────────
        if intent == "OPEN_URL":
            url = meta.get("url", "")
            speak_fn(f"Opening {entity}…")
            webbrowser.open(url)
            confirm(f"{entity} opened.")
            # ← record context
            if ctx:
                ctx.set_app(entity.lower(), url=url, intent="OPEN_URL")
            return True

        # ── Open App ─────────────────────────────────────────────────────────
        if intent == "OPEN_APP":
            app_key = entity.lower().strip()
            exe     = _APP_MAP.get(app_key, app_key)
            label   = entity.title() or app_key
            speak_fn(f"Opening {label}…")
            subprocess.Popen(exe, shell=True)
            confirm(f"{label} opened.")
            # ← record context (use URL from meta if available, e.g. YouTube)
            if ctx:
                url = meta.get("url", "")
                ctx.set_app(app_key, url=url, intent="OPEN_APP")
            return True

        # ── Web search ───────────────────────────────────────────────────────
        if intent == "SEARCH_WEB":
            # Context: if last_app is youtube, search on youtube instead
            if ctx and ctx.last_app == "youtube":
                query = entity or "that"
                speak_fn(f"Searching YouTube for {query}…")
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(url)
                confirm(f"YouTube results for {query}.")
                return True

            query = entity or "that"
            speak_fn(f"Searching for {query}…")
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            confirm(f"Here are the results for {query}.")
            return True

        # ── YouTube search ───────────────────────────────────────────────────
        if intent == "YOUTUBE_SEARCH":
            query = entity or "music"
            speak_fn(f"Searching YouTube for {query}…")
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(url)
            confirm(f"Playing YouTube results for {query}.")
            return True

        # ── Play music ───────────────────────────────────────────────────────
        if intent == "PLAY_MUSIC":
            # Context: if last_app is youtube, play music on youtube
            if ctx and ctx.last_app == "youtube":
                speak_fn("Playing music on YouTube…")
                webbrowser.open("https://www.youtube.com/results?search_query=music")
                confirm("Playing music on YouTube.")
                return True
            if ctx and ctx.last_app == "spotify":
                speak_fn("Playing music on Spotify…")
                webbrowser.open("https://open.spotify.com")
                confirm("Spotify opened for music.")
                return True

            speak_fn("Playing music…")
            try:
                from commands.command_music import play_music
                play_music()
            except Exception:
                webbrowser.open("https://open.spotify.com")
            confirm("Music is playing.")
            return True

        # ── Weather ──────────────────────────────────────────────────────────
        if intent == "WEATHER":
            city = entity or "your city"
            speak_fn(f"Checking weather for {city}…")
            try:
                from commands.command_weather import get_weather
                get_weather(city)
            except Exception:
                speak_fn(f"Sorry, I couldn't fetch weather for {city}.")
            return True

        # ── Time ─────────────────────────────────────────────────────────────
        if intent == "TIME":
            now = _dt.datetime.now().strftime("%I:%M %p")
            speak_fn(f"The current time is {now}.")
            return True

        # ── Date ─────────────────────────────────────────────────────────────
        if intent == "DATE":
            today = _dt.datetime.now().strftime("%A, %B %d, %Y")
            speak_fn(f"Today is {today}.")
            return True

        # ── System control ───────────────────────────────────────────────────
        if intent == "SYSTEM_CONTROL":
            from commands.command_executor import _system_action
            speak_fn(f"Performing {entity}…")
            _system_action(step.raw_segment, speak_fn)
            return True

        # ── Note / Todo / Reminder ───────────────────────────────────────────
        if intent == "NOTE_TASK":
            from commands.command_executor import _note_task
            _note_task(entity, step.raw_segment, speak_fn)
            return True

        # ── News ─────────────────────────────────────────────────────────────
        if intent == "NEWS":
            speak_fn("Fetching the latest news…")
            from commands.command_news import get_news
            get_news()
            return True

        # ── Small talk / joke ─────────────────────────────────────────────────
        if intent == "SMALL_TALK":
            if "joke" in entity:
                from commands.command_jokes import tell_joke
                tell_joke()
            return True

        # ── Fallback ─────────────────────────────────────────────────────────
        speak_fn(f"I'm not sure how to handle '{step.raw_segment}', skipping.")
        return False

    except Exception as exc:
        print(f"[Planner] ❌ Step failed ({intent}/{entity}): {exc}")
        speak_fn(f"Sorry, something went wrong with {entity or 'that step'}.")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CommandPlanner  –  main class
# ─────────────────────────────────────────────────────────────────────────────

class CommandPlanner:
    """
    Wraps the multi-step planning pipeline with context memory.

    Usage
    -----
        planner = CommandPlanner(
            speak_female = rm.speak,
            speak_jarvis = lambda t: rm.speak(t, use_female=False),
        )

        # Multi-step command:
        handled = planner.try_multi("open youtube and play a song on that")

        # Single command with context reference:
        handled = planner.try_context("play song on that")

        if not handled:
            # Let normal single-command pipeline run
    """

    def __init__(
        self,
        speak_female : Callable[[str], None],
        speak_jarvis : Callable[[str], None] | None = None,
        step_delay   : float = 0.6,
        ctx          : ContextMemory | None = None,
    ):
        """
        Parameters
        ----------
        speak_female : TTS function for action announcements (female voice)
        speak_jarvis : TTS function for confirmations (Jarvis voice)
        step_delay   : seconds to pause between steps (UX breathing room)
        ctx          : ContextMemory instance (defaults to module singleton)
        """
        self._speak_f = speak_female
        self._speak_j = speak_jarvis or speak_female
        self._delay   = step_delay
        self._ctx     = ctx or ctx_mem      # use shared singleton if not given

    # ── Public ───────────────────────────────────────────────────────────────

    def try_multi(self, text: str, stop_on_failure: bool = True) -> bool:
        """
        Attempt multi-step execution.

        First resolves any contextual references in the full text, then
        splits into steps and runs them sequentially.

        Returns
        -------
        True  – 2 or more steps were found and executed (caller should skip
                its own single-command pipeline for this utterance).
        False – only 0 or 1 steps found; caller handles normally.
        """
        # Pre-pass: resolve "on that" BEFORE splitting, so context propagates
        text_resolved = self._resolve_full(text)
        steps = plan(text_resolved, ctx=self._ctx)

        if len(steps) < 2:
            return False

        print(f"[Planner] {len(steps)}-step plan: {steps}")
        self._speak_f(f"Sure, I'll handle {len(steps)} things for you.")

        for i, step in enumerate(steps, 1):
            print(f"[Planner] Executing step {i}/{len(steps)}: {step}")
            ok = execute_step(step, self._speak_f, self._speak_j, ctx=self._ctx)
            if not ok and stop_on_failure:
                self._speak_j("Stopped due to an error in a previous step.")
                break
            if i < len(steps):
                time.sleep(self._delay)

        return True

    def try_context(self, text: str) -> bool:
        """
        Handle a SINGLE command that contains a contextual reference
        ("play song on that", "search python book on it", "us par gana chalao").

        Returns True if a reference was detected AND successfully resolved
        and executed.  Returns False if no reference found (caller continues
        normally).
        """
        if not self._ctx.has_reference(text):
            return False                     # no "on that" → normal path
        if not self._ctx.last_app:
            self._speak_f("I'm not sure which app you're referring to.")
            return True                      # handled (with an error message)

        resolved = self._ctx.resolve_reference(text)
        print(f"[Planner] Context resolved: '{text}' → '{resolved}'")
        step = parse_step(resolved, ctx=self._ctx)
        if step is None:
            self._speak_f("I understood the reference but couldn't figure out the action.")
            return True

        self._speak_f(f"Got it — using {self._ctx.last_app.title()}.")
        execute_step(step, self._speak_f, self._speak_j, ctx=self._ctx)
        return True

    def force_multi(self, text: str) -> list[Step]:
        """
        Parse and return the plan without executing it.
        Useful for debugging or pre-flight checks.
        """
        return plan(text, ctx=self._ctx)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_full(self, text: str) -> str:
        """
        Resolve contextual references in the raw text BEFORE splitting.
        This handles cases like "open youtube and play a song on that" where
        'on that' refers to 'youtube' which was just mentioned in the SAME
        sentence (not a stored context).
        """
        norm = text.lower()
        # Does the sentence contain an app name AND "on that" after it?
        app_names = list(_APP_MAP.keys()) + [
            "youtube", "gmail", "google", "maps", "whatsapp",
            "spotify", "discord", "chrome", "firefox", "edge",
        ]
        for app in sorted(app_names, key=len, reverse=True):
            if app in norm:
                # Temporarily set last_app to the mentioned app so resolution works
                # Only if no stored context exists yet
                if not self._ctx.last_app:
                    self._ctx.set_app(app, intent="OPEN_APP")
                break

        return self._ctx.resolve_reference(text) if self._ctx.has_reference(text) else text


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    def _print_speak(msg):
        print(f"  🔊 Female: {msg}")

    def _jarvis_speak(msg):
        print(f"  🤖 Jarvis: {msg}")

    planner = CommandPlanner(
        speak_female=_print_speak,
        speak_jarvis=_jarvis_speak,
        step_delay=0.3,
    )

    sentences = [
        "open youtube and play a song on that",
        "open chrome and search a good python book on it",
        "open spotify and play music there",
        "play music then open youtube and search lofi",
        "what's the time aur mausam batao",
        "open notepad fir take a note then set reminder for meeting at 5pm",
        "open gmail and check latest news then tell me a joke",
    ]

    single_context_tests = [
        ("open youtube",      "play song on that"),
        ("open spotify",      "gana chalao wahan"),
        ("open google maps",  "search restaurants on it"),
    ]

    if len(sys.argv) > 1:
        sentences = [" ".join(sys.argv[1:])]
        single_context_tests = []

    print("\n" + "═"*64)
    print(" MULTI-STEP TESTS")
    print("═"*64)
    for sentence in sentences:
        print(f"\n{'─'*60}")
        print(f"  Input: \"{sentence}\"")
        steps = plan(sentence, ctx=planner._ctx)
        if not steps:
            print("  No recognised steps.")
        else:
            for idx, s in enumerate(steps, 1):
                print(f"  Step {idx}: {s}")

    print("\n" + "═"*64)
    print(" CONTEXT-REFERENCE TESTS")
    print("═"*64)
    for first_cmd, follow_up in single_context_tests:
        print(f"\n{'─'*60}")
        print(f"  [1] User: \"{first_cmd}\"")
        step1 = parse_step(first_cmd, ctx=planner._ctx)
        if step1:
            execute_step(step1, _print_speak, _jarvis_speak, ctx=planner._ctx)
        print(f"  [2] User: \"{follow_up}\"")
        handled = planner.try_context(follow_up)
        if not handled:
            print("  → No contextual reference detected, would go to normal pipeline.")
