"""
command_executor.py  –  Intent → Action router  (return-value edition)
=======================================================================
Every public function returns  (success: bool, message: str).
NOTHING speaks directly — the caller (main.py / ResponseManager) owns TTS.

This keeps speaking and execution cleanly separated:
  • No duplicate voice output
  • Caller decides how/when to speak success vs. error messages
  • Easy to unit-test without a live TTS engine

Usage
-----
    from commands.command_executor import execute

    ok, msg = execute(intent_result)
    if ok:
        rm.post_action(intent, entity)
    else:
        rm.speak(msg, use_female=False)   # speak the error directly
"""

import os
import subprocess
import webbrowser
import datetime
import logging

# ── Existing modules ────────────────────────────────────────────────────────
from core.runtime.task_automation import do_task, system_control
logger = logging.getLogger(__name__)


def _missing(name: str):
    def _inner(*args, **kwargs):
        raise RuntimeError(f"Legacy command '{name}' is not available in this build.")
    return _inner


try:
    from commands.command_weather import get_weather
except Exception:
    get_weather = _missing("get_weather")
try:
    from commands.command_calculator import calculate
except Exception:
    calculate = _missing("calculate")
try:
    from commands.command_reminder import set_reminder
except Exception:
    set_reminder = _missing("set_reminder")
try:
    from commands.command_jokes import tell_joke
except Exception:
    tell_joke = _missing("tell_joke")
try:
    from commands.command_news import get_news
except Exception:
    get_news = _missing("get_news")
try:
    from commands.command_music import play_music
except Exception:
    play_music = _missing("play_music")
try:
    from commands.command_system import system_info
except Exception:
    system_info = _missing("system_info")
try:
    from commands.command_hardware import wifi_control
except Exception:
    wifi_control = _missing("wifi_control")
try:
    from commands.command_calendar import get_calendar_events
except Exception:
    get_calendar_events = _missing("get_calendar_events")
try:
    from commands.command_todo import add_todo, list_todos
except Exception:
    add_todo = _missing("add_todo")
    list_todos = _missing("list_todos")
try:
    from commands.command_notes import take_note
except Exception:
    take_note = _missing("take_note")
try:
    from commands.command_dict import define_word
except Exception:
    define_word = _missing("define_word")
try:
    from commands.command_battery import battery_status
except Exception:
    battery_status = _missing("battery_status")
try:
    from commands.command_bluetooth import bluetooth_control
except Exception:
    bluetooth_control = _missing("bluetooth_control")
try:
    from commands.command_quotes import daily_quote
except Exception:
    daily_quote = _missing("daily_quote")
try:
    from commands.command_youtube import search_youtube, extract_youtube_topic
except Exception:
    search_youtube = _missing("search_youtube")
    extract_youtube_topic = lambda *_args, **_kwargs: ""
try:
    from commands.command_stock import get_stock_price
except Exception:
    get_stock_price = _missing("get_stock_price")
try:
    from commands.command_google_search import google_search
except Exception:
    google_search = _missing("google_search")
try:
    from commands.command_screenshot import take_screenshot
except Exception:
    take_screenshot = _missing("take_screenshot")
try:
    from commands.command_random_number import random_number
except Exception:
    random_number = _missing("random_number")
try:
    from commands.command_horoscope import get_horoscope
except Exception:
    get_horoscope = _missing("get_horoscope")


def speak(_text: str):
    return None

# ── App name → executable mapping ───────────────────────────────────────────
APP_MAP: dict[str, str] = {
    "chrome"        : "chrome",
    "google chrome" : "chrome",
    "firefox"       : "firefox",
    "edge"          : "msedge",
    "microsoft edge": "msedge",
    "edge browser"  : "msedge",
    "notepad"       : "notepad",
    "calculator"    : "calc",
    "word"          : "WINWORD",
    "excel"         : "EXCEL",
    "powerpoint"    : "POWERPNT",
    "vscode"        : "code",
    "vs code"       : "code",
    "visual studio code": "code",
    "paint"         : "mspaint",
    "explorer"      : "explorer",
    "file explorer" : "explorer",
    "task manager"  : "taskmgr",
    "spotify"       : "spotify",
    "vlc"           : "vlc",
    "discord"       : "discord",
    "teams"         : "teams",
    "zoom"          : "zoom",
    "cmd"           : "cmd",
    "command prompt": "cmd",
    "powershell"    : "powershell",
    "brave"         : "brave",
    "opera"         : "opera",
    "skype"         : "skype",
    "telegram"      : "telegram",
    "whatsapp"      : "WhatsApp",
    "camera"        : "microsoft.windows.camera:",   # UWP URI
}

# URL-based apps (open in browser instead of subprocess)
URL_MAP: dict[str, str] = {
    "youtube"      : "https://youtube.com",
    "gmail"        : "https://mail.google.com",
    "google"       : "https://google.com",
    "maps"         : "https://maps.google.com",
    "google maps"  : "https://maps.google.com",
    "whatsapp web" : "https://web.whatsapp.com",
    "netflix"      : "https://netflix.com",
    "github"       : "https://github.com",
    "instagram"    : "https://instagram.com",
    "facebook"     : "https://facebook.com",
    "twitter"      : "https://twitter.com",
    "linkedin"     : "https://linkedin.com",
}


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers — all return (bool, str)
# ─────────────────────────────────────────────────────────────────────────────

def _open_app(entity: str) -> tuple[bool, str]:
    """Launch an application or open a URL by entity name."""
    key = entity.lower().strip()

    # URL-based apps first
    if key in URL_MAP:
        try:
            webbrowser.open(URL_MAP[key])
            return True, f"{entity.title()} opened."
        except Exception as e:
            return False, f"Couldn't open {entity.title()}: {e}"

    # Native app
    exe = APP_MAP.get(key, key)
    try:
        if exe.endswith(":"):            # UWP URI (e.g. camera)
            os.startfile(exe)
        else:
            subprocess.Popen(exe, shell=True)
        return True, f"{entity.title()} opened."
    except Exception as e:
        return False, f"Sorry, I couldn't open {entity.title()}. {e}"


def _close_window() -> tuple[bool, str]:
    """Close the active foreground window using Alt+F4."""
    try:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return True, "Window closed."
    except ImportError:
        try:
            os.system(
                "powershell -command \""
                "$proc = (Get-Process | Where-Object {$_.MainWindowHandle -ne 0} "
                "| Sort-Object CPU -Descending | Select-Object -First 1); "
                "Stop-Process -Id $proc.Id -Force\""
            )
            return True, "Closed the active window."
        except Exception as e:
            return False, f"Couldn't close the window: {e}"


def _search_web(entity: str) -> tuple[bool, str]:
    """Open a Google search for entity."""
    if not entity:
        return False, "What would you like me to search for?"
    url = f"https://www.google.com/search?q={entity.replace(' ', '+')}"
    webbrowser.open(url)
    return True, f"Search results for {entity} are ready."


def _system_action(raw: str) -> tuple[bool, str]:
    """Handle system commands: shutdown, restart, lock, volume, wifi …"""
    raw = raw.lower()
    if "shutdown" in raw or "shut down" in raw:
        os.system("shutdown /s /t 1")
        return True, "Shutting down."
    if "restart" in raw or "reboot" in raw:
        os.system("shutdown /r /t 1")
        return True, "Restarting."
    if "lock" in raw:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return True, "Screen locked."
    if "wifi on" in raw:
        wifi_control(True)
        return True, "Wi-Fi turned on."
    if "wifi off" in raw:
        wifi_control(False)
        return True, "Wi-Fi turned off."
    if "bluetooth on" in raw:
        bluetooth_control(True)
        return True, "Bluetooth turned on."
    if "bluetooth off" in raw:
        bluetooth_control(False)
        return True, "Bluetooth turned off."
    if "volume up" in raw or "volume badhao" in raw:
        try:
            import pyautogui
            pyautogui.press("volumeup", presses=5)
            return True, "Volume increased."
        except ImportError:
            return False, "Volume control requires pyautogui."
    if "volume down" in raw or "volume kam" in raw:
        try:
            import pyautogui
            pyautogui.press("volumedown", presses=5)
            return True, "Volume decreased."
        except ImportError:
            return False, "Volume control requires pyautogui."
    if "mute" in raw:
        try:
            import pyautogui
            pyautogui.press("volumemute")
            return True, "Muted."
        except ImportError:
            return False, "Mute requires pyautogui."
    if "screenshot" in raw:
        try:
            take_screenshot()
            return True, "Screenshot taken."
        except Exception as e:
            return False, f"Screenshot failed: {e}"
    if "system info" in raw or "system" in raw:
        try:
            system_info()
            return True, "System info retrieved."
        except Exception as e:
            return False, f"System info error: {e}"
    return False, "I'm not sure which system command you meant."


def _info_query(entity: str, raw: str) -> tuple[bool, str]:
    """Handle info queries: time, date, weather, battery, stock, horoscope."""
    if "time" in entity or "time" in raw or "samay" in raw:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return True, f"The current time is {now}."
    if "weather" in entity or "weather" in raw or "mausam" in raw:
        city = entity if entity not in ("weather", "") else "your city"
        try:
            get_weather(city)
            return True, ""
        except Exception as e:
            return False, f"Couldn't fetch weather: {e}"
    if "date" in entity or "date" in raw or "aaj" in raw:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return True, f"Today is {today}."
    if "battery" in entity or "battery" in raw:
        try:
            battery_status()
            return True, ""
        except Exception as e:
            return False, f"Battery check failed: {e}"
    if "stock" in entity or "stock" in raw:
        return False, "Which stock would you like to check?"
    if "horoscope" in entity or "horoscope" in raw:
        try:
            get_horoscope("aries")
            return True, ""
        except Exception as e:
            return False, f"Horoscope error: {e}"
    # Generic fallback
    try:
        do_task(raw, lambda m: None)    # silence speak in do_task
        return True, ""
    except Exception as e:
        return False, str(e)


def _media_action(entity: str, raw: str) -> tuple[bool, str]:
    """Handle media commands."""
    # Fine-grained intent from keyword_engine preserved in raw via ke_intent
    if "youtube" in raw.lower():
        # Always extract a clean topic — works for English, Hindi, Hinglish
        term = extract_youtube_topic(raw)
        # If the entity slot is already clean and specific, prefer it
        if not term and entity:
            term = entity
        if term:
            search_youtube(term)
            return True, f"Searching YouTube for {term}."
        # No topic found → open homepage
        search_youtube("")
        return True, "Opening YouTube."

    if "play" in raw or "music" in raw or "song" in raw or "gana" in raw:
        ok, msg = play_music()
        return ok, msg

    return True, "Media request handled."


def _note_task(entity: str, raw: str) -> tuple[bool, str]:
    """Handle notes, reminders, todos."""
    if "reminder" in raw or "remind" in raw or "yaad dilao" in raw:
        msg = entity or raw
        try:
            set_reminder(msg)
            return True, "Reminder set."
        except Exception as e:
            return False, f"Reminder error: {e}"
    if "note" in raw:   
        try:
            take_note(entity or raw, speak)
            return True, "Note saved."
        except Exception as e:
            print("Note error:", e)
            return False, "Failed to save note."
    if "add task" in raw or "add todo" in raw or "kaam add" in raw:
        task = entity or raw
        try:
            add_todo(task)
            return True, f"Task added: {task}."
        except Exception as e:
            return False, f"Todo error: {e}"
    if "show" in raw or "list" in raw:
        try:
            list_todos()
            return True, ""
        except Exception as e:
            return False, f"List error: {e}"
    if "calendar" in raw or "events" in raw:
        try:
            get_calendar_events()
            return True, ""
        except Exception as e:
            return False, f"Calendar error: {e}"
    return False, "Sure, what would you like me to note?"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def execute(intent_result: dict) -> tuple[bool, str]:
    """
    Route an intent result dict to the appropriate command.

    Parameters
    ----------
    intent_result : dict from brain.intent_engine.detect_intent() or keyword_engine.keyword_match()
                    Keys: intent, entity, confidence, raw
                    Optional key: ke_intent (fine-grained keyword engine intent)

    Returns
    -------
    (success: bool, message: str)
        success=True  → command ran OK; message is a confirmation (may be "")
        success=False → command failed; message is an error to speak
    """
    intent    = intent_result.get("intent", "UNKNOWN")
    ke_intent = intent_result.get("ke_intent", intent)   # finer-grained if available
    entity    = intent_result.get("entity", "")
    raw       = intent_result.get("raw", "")

    print(f"[Executor] intent={intent} ke={ke_intent} entity='{entity}'")

    # ── OPEN_APP ─────────────────────────────────────────────────────────────
    if intent == "OPEN_APP":
        target = entity if entity else raw
        return _open_app(target)

    # ── CLOSE_WINDOW ─────────────────────────────────────────────────────────
    if intent == "CLOSE_WINDOW":
        return _close_window()

    # ── SEARCH_WEB ───────────────────────────────────────────────────────────
    if intent == "SEARCH_WEB":
        return _search_web(entity)

    # ── SYSTEM_CONTROL ───────────────────────────────────────────────────────
    if intent == "SYSTEM_CONTROL":
        return _system_action(raw)

    # ── MEDIA_CONTROL (includes PLAY_MUSIC, YOUTUBE_MUSIC) ───────────────────
    if intent == "MEDIA_CONTROL":
        # Use ke_intent for finer-grained routing
        if ke_intent == "YOUTUBE_MUSIC":
            webbrowser.open("https://music.youtube.com")
            return True, "Playing music on YouTube Music."
        if ke_intent == "PLAY_MUSIC":
            ok, msg = play_music()
            return ok, msg
        return _media_action(entity, raw)

    # ── INFO_QUERY (time, date, weather, battery …) ───────────────────────────
    if intent == "INFO_QUERY":
        # Fine-grained routing via ke_intent
        if ke_intent == "TIME_QUERY":
            now = datetime.datetime.now().strftime("%I:%M %p")
            return True, f"The current time is {now}."
        if ke_intent == "DATE_QUERY":
            today = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return True, f"Today is {today}."
        if ke_intent == "WEATHER":
            city = entity or "your city"
            try:
                get_weather(city)
                return True, ""
            except Exception as e:
                return False, f"Couldn't fetch weather: {e}"
        return _info_query(entity, raw)

    # ── NOTE_TASK ─────────────────────────────────────────────────────────────
    if intent == "NOTE_TASK":
        return _note_task(entity, raw)

    # ── CALCULATOR ────────────────────────────────────────────────────────────
    if intent == "CALCULATOR":
        expression = entity or raw
        try:
            calculate(expression)
            return True, ""
        except Exception as e:
            return False, f"Calculation error: {e}"

    # ── NEWS ──────────────────────────────────────────────────────────────────
    if intent == "NEWS":
        try:
            get_news()
            return True, ""
        except Exception as e:
            return False, f"News error: {e}"

    # ── SMALL_TALK ────────────────────────────────────────────────────────────
    if intent == "SMALL_TALK":
        if "joke" in raw:
            try:
                tell_joke()
                return True, ""
            except Exception as e:
                return False, f"Joke error: {e}"
        if "quote" in raw or "motivation" in raw:
            try:
                daily_quote()
                return True, ""
            except Exception as e:
                return False, f"Quote error: {e}"
        return True, ""   # confirmation via ResponseManager is enough

    # ── SCREEN_READ (Vision module) ───────────────────────────────────────────
    if intent == "SCREEN_READ":
        try:
            from brain.reasoning.jarvis_vision import vision
            text = vision.read_screen_spoken()
            return True, text
        except Exception as e:
            return False, f"Screen read failed: {e}"

    # ── CLICK_ELEMENT (Control module) ────────────────────────────────────────
    if intent == "CLICK_ELEMENT":
        target = entity or raw
        try:
            from core.runtime.jarvis_control import ctrl
            ok = ctrl.click_element(target)
            if ok:
                return True, f"Clicked {target}."
            return False, f"I couldn't find '{target}' on the screen."
        except Exception as e:
            return False, f"Click failed: {e}"

    # ── RESEARCH (Internet Brain) ─────────────────────────────────────────────
    if intent == "RESEARCH":
        query = entity or raw
        try:
            from brain.reasoning.jarvis_internet import internet
            if not internet.is_online():
                return False, internet.offline_warning()
            result = internet.search_and_summarize(query)
            if result["ok"]:
                return True, result["summary"]
            return False, result["summary"]
        except Exception as e:
            return False, f"Research failed: {e}"

    # ── UNKNOWN → fallback ────────────────────────────────────────────────────
    try:

        do_task(raw, lambda m: None)
        return True, ""
    except Exception as e:
        return False, f"I couldn't handle that: {e}"
