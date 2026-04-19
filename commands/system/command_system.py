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
from typing import Optional

logger = logging.getLogger(__name__)

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
    if "shutdown" in q: return "SYSTEM_ACTION:shutdown"
    if "restart" in q: return "SYSTEM_ACTION:restart"

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
    dirs = ["Desktop", "Documents", "Downloads", "Pictures"]
    for d in dirs:
        if name.lower() in d.lower():
            os.startfile(os.path.join(path, d))
            return f"Opening {d}."
    return "Folder not found."

def write_to_notepad(content: str) -> str:
    """Type content into Notepad using pyautogui."""
    import time
    try:
        import pyautogui
        import pygetwindow as gw
    except Exception:
        return "Sir, notepad typing ke liye pyautogui aur pygetwindow install hone chahiye."

    if not content:
        return "Sir, kya likhna hai notepad mein? Aapne kuch bataya nahi."

    # 1. Ensure Notepad is open
    notepads = gw.getWindowsWithTitle('Notepad')
    if not notepads:
        os.startfile("notepad.exe")
        time.sleep(1.5) # Wait for launch
        notepads = gw.getWindowsWithTitle('Notepad')
    
    if notepads:
        try:
            # 2. Focus window
            win = notepads[0]
            if win.isMinimized: win.restore()
            win.activate()
            time.sleep(0.5)
            
            # 3. Type content
            pyautogui.write(content, interval=0.01)
            return f"Sir, maine notepad mein '{content[:20]}...' likh diya hai."
        except Exception as e:
            logger.error(f"Notepad write error: {e}")
            return "Sir, notepad mein likhne mein kuch dikkat aa rahi hai."
    
    return "Sir, main notepad open nahi kar pa rahi hoon."

def execute_pc_action(action: str):
    """External trigger for shutdown/restart."""
    if action == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "1"], shell=False)
    elif action == "restart":
        subprocess.run(["shutdown", "/r", "/t", "1"], shell=False)
