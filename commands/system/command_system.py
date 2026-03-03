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
from typing import Optional

logger = logging.getLogger(__name__)

# Predefined standard apps
APP_COMMANDS = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "vs code": "code",
    "notepad": "notepad.exe",
    "calculator": "calc.exe"
}

def run(query: str) -> Optional[str]:
    """Execute system-level tasks safely."""
    q = query.lower().strip()

    # 1. App Launching (Safe via startfile or direct list)
    if q.startswith("open "):
        target = q.replace("open ", "").strip()
        
        for name, exe in APP_COMMANDS.items():
            if name in target:
                try:
                    # os.startfile is safer and uses system associations on Windows
                    os.startfile(exe) if name != "vs code" else subprocess.Popen(["code"], shell=False)
                    return f"Opening {name.title()}."
                except Exception:
                    return f"I couldn't launch {name}."

        if "folder" in target:
            folder_name = target.replace("folder", "").strip()
            return _open_folder(folder_name)

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

def execute_pc_action(action: str):
    """External trigger for shutdown/restart."""
    if action == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "1"], shell=False)
    elif action == "restart":
        subprocess.run(["shutdown", "/r", "/t", "1"], shell=False)
