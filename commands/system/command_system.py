"""
command_system.py – Hardened System Controller
==============================================
No shell=True. Safe executable launching.
"""

from __future__ import annotations
import os
import subprocess
import ctypes
import logging
import webbrowser
import time
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

DANGEROUS_ACTIONS = {"shutdown", "restart", "sleep", "logoff"}
_pending = {"action": None, "ts": 0}

# Predefined standard apps
APP_COMMANDS = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "vs code": "code",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "browser": "msedge.exe"
}

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "github": "https://github.com",
    "whatsapp": "https://web.whatsapp.com"
}

def run(query: str) -> Optional[str]:
    """Execute system-level tasks safely."""
    q = query.lower().strip()

    # 1. App Launching (Safe via startfile or direct list)
    if q.startswith("open "):
        target = q.replace("open ", "").strip()
        
        # 1.1 Local Apps
        for name, exe in APP_COMMANDS.items():
            if name in target:
                try:
                    os.startfile(exe) if name != "vs code" else subprocess.Popen(["code"], shell=False)
                    return f"Opening {name.title()} sir."
                except Exception:
                    pass

        # 1.2 Websites
        for name, url in WEBSITES.items():
            if name in target:
                try:
                    webbrowser.open(url)
                    return f"Opening {name.title()} for you sir."
                except Exception:
                    pass

        # 1.3 Generic Folders
        if "folder" in target:
            folder_name = target.replace("folder", "").strip()
            return _open_folder(folder_name)

        # 1.4 Fallback: Open in browser (Search or URL)
        try:
            # If it looks like a domain, open directly
            if "." in target and " " not in target:
                url = f"https://{target}" if not target.startswith("http") else target
                webbrowser.open(url)
                return f"Opening {target}."
            else:
                # Search Google
                search_url = f"https://www.google.com/search?q={target}"
                webbrowser.open(search_url)
                return f"Searching for {target} on Google sir."
        except Exception:
            return f"I couldn't open {target}."

    # 2. System Power (Through brain -> main protocol)
    if _pending["action"]:
        if "yes" in q or "haan" in q or "confirm" in q:
            action = _pending["action"]
            _pending["action"] = None
            return execute_pc_action(action, confirmed=True)
        else:
            _pending["action"] = None

    if "shutdown" in q: return execute_pc_action("shutdown")
    if "restart" in q: return execute_pc_action("restart")

    if "lock" in q and "pc" in q:
        ctypes.windll.user32.LockWorkStation()
        return "PC locked."

    # 3. Media
    if "volume up" in q:
        _change_vol(0xAF)
        return "Increasing volume."
    if "volume down" in q:
        _change_vol(0xAE)
        return "Decreasing volume."
    if "mute" in q:
        _change_vol(0xAD)
        return "Volume toggled."

    return None

def _change_vol(vkey: int):
    for _ in range(5):
        ctypes.windll.user32.keybd_event(vkey, 0, 0, 0)

def _open_folder(name: str) -> str:
    path = os.path.expanduser("~")
    dirs = ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"]
    
    # Strict matching instead of substring `in d.lower()`
    matched_dir = None
    for d in dirs:
        if name.lower().strip() == d.lower():
            matched_dir = d
            break
            
    if matched_dir:
        target_path = os.path.abspath(os.path.join(path, matched_dir))
        # Ensure it doesn't escape the user profile
        if target_path.startswith(os.path.abspath(path)):
            os.startfile(target_path)
            return f"Opening {matched_dir}."
            
    return "Folder not found or access denied."

def search_file(query: str) -> str:
    """Uses Windows search-ms protocol to open file explorer with search results."""
    if not query:
        return "Kaunsi file dhundni hai sir?"
    
    try:
        user_home = os.path.expanduser("~")
        search_url = f"search-ms:query={query}&crumb=location:{user_home}"
        os.startfile(search_url)
        return f"Sir, maine aapke liye '{query}' search kar di hai. File explorer me results check karein."
    except Exception as e:
        logger.error(f"File search failed: {e}")
        return "Sir, file search open karne mein kuch error aa rahi hai."

def handle_desktop_control(text: str, entity: str) -> str:
    """Parse string command to jarvis_control actions."""
    from core.runtime.jarvis_control import ctrl
    
    text_lower = text.lower()
    
    if "scroll down" in text_lower:
        ctrl.scroll_down(3)
        return "Scrolling down sir."
    elif "scroll up" in text_lower:
        ctrl.scroll_up(3)
        return "Scrolling up sir."
    elif "click" in text_lower:
        if entity:
            ctrl.click_element(entity)
            return f"Clicking on {entity}."
        return "Kahan click karu sir?"
    elif "type" in text_lower:
        if entity:
            ctrl.type_text(entity)
            return f"Typing {entity}."
        return "Kya type karu sir?"
    elif "new tab" in text_lower:
        ctrl.open_new_tab()
        return "Opening new tab."
    elif "close tab" in text_lower:
        ctrl.close_tab()
        return "Closing tab."
    elif "copy" in text_lower:
        ctrl.select_all_and_copy()
        return "Copied to clipboard."
    elif "press" in text_lower:
        ctrl.press_key(entity)
        return f"Pressing {entity}."
    
    return "Sir, main ye desktop action nahi samajh paya."

def write_to_notepad(content: str) -> str:
    """Safely write content to Notepad using a temp file."""
    if not content:
        return "Sir, kya likhna hai notepad mein? Aapne kuch bataya nahi."

    try:
        path = os.path.join(tempfile.gettempdir(), "jarvis_note.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        os.startfile(path)
        return f"Sir, maine notepad mein '{content[:20]}...' likh diya hai."
    except Exception as e:
        logger.error(f"Notepad write error: {e}")
        return "Sir, notepad open karne mein kuch dikkat aa rahi hai."

def execute_pc_action(action: str, confirmed: bool = False):
    """External trigger for shutdown/restart with confirmation."""
    if action in DANGEROUS_ACTIONS and not confirmed:
        _pending["action"] = action
        _pending["ts"] = time.time()
        return f"Confirm karo — {action} karna hai? 10 second me 'haan confirm' bolo."

    if action in DANGEROUS_ACTIONS and time.time() - _pending["ts"] > 10:
        return "Timeout, cancel kar diya."

    logger.info(f"Executing PC action: {action}")
    if action == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "1"], shell=False)
        return "Shutting down the PC sir."
    elif action == "restart":
        subprocess.run(["shutdown", "/r", "/t", "1"], shell=False)
        return "Restarting the PC sir."
    return None
