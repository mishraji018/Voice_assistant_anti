"""
startup_manager.py  –  Windows auto-start helper
=================================================
Registers (or removes) Jarvis from Windows startup so it launches
automatically when the user logs in.

Two methods are available:
  METHOD A  (preferred)   – writes a .lnk shortcut to the user's
                             shell:startup folder via winshell,
                             with ctypes/win32 fallback.
  METHOD B  (fallback)    – creates a Task Scheduler entry via
                             schtasks.exe when the shortcuts API
                             is unavailable.

Public API
----------
    from startup_manager import enable_startup, disable_startup, startup_status

    enable_startup(path_to_jarvis_exe)   # register
    disable_startup()                    # remove
    startup_status()                     # "method_a" | "method_b" | "none"
"""

import os
import sys
import subprocess
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME    = "Jarvis"
TASK_NAME   = "JarvisAutoStart"          # Task Scheduler task name
STARTUP_DIR = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
SHORTCUT    = STARTUP_DIR / f"{APP_NAME}.lnk"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _method_a_create(target: str) -> bool:
    """
    Create a .lnk shortcut in the startup folder.
    Tries winshell first; falls back to a raw win32com / ctypes approach.
    """
    target = str(Path(target).resolve())
    work_dir = str(Path(target).parent)

    # ── winshell (pip install winshell) ───────────────────────────────────────
    try:
        import winshell                               # type: ignore
        with winshell.shortcut(str(SHORTCUT)) as sc:
            sc.path        = target
            sc.working_directory = work_dir
            sc.description = f"Start {APP_NAME} on login"
        print(f"[Startup] Method A (winshell): shortcut created → {SHORTCUT}")
        return True
    except ImportError:
        pass
    except Exception as exc:
        print(f"[Startup] winshell failed: {exc}")

    # ── win32com (included with pywin32) ─────────────────────────────────────
    try:
        import win32com.client                        # type: ignore
        shell    = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(SHORTCUT))
        shortcut.Targetpath       = target
        shortcut.WorkingDirectory = work_dir
        shortcut.Description      = f"Start {APP_NAME} on login"
        shortcut.save()
        print(f"[Startup] Method A (win32com): shortcut created → {SHORTCUT}")
        return True
    except ImportError:
        pass
    except Exception as exc:
        print(f"[Startup] win32com failed: {exc}")

    # ── ctypes / PowerShell fallback ─────────────────────────────────────────
    try:
        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell;"
            f"$sc = $ws.CreateShortcut('{SHORTCUT}');"
            f"$sc.TargetPath = '{target}';"
            f"$sc.WorkingDirectory = '{work_dir}';"
            f"$sc.Description = 'Start {APP_NAME} on login';"
            f"$sc.Save()"
        )
        result = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            print(f"[Startup] Method A (PowerShell): shortcut created → {SHORTCUT}")
            return True
        print(f"[Startup] PowerShell error: {result.stderr.decode(errors='ignore')}")
    except Exception as exc:
        print(f"[Startup] PowerShell fallback failed: {exc}")

    return False


def _method_a_remove() -> bool:
    """Delete the startup shortcut if it exists."""
    if SHORTCUT.exists():
        try:
            SHORTCUT.unlink()
            print(f"[Startup] Method A: shortcut removed from {SHORTCUT}")
            return True
        except Exception as exc:
            print(f"[Startup] Could not remove shortcut: {exc}")
    return False


def _method_b_create(target: str) -> bool:
    """
    Register a Task Scheduler task that runs Jarvis at user logon.
    Uses schtasks.exe (built into every Windows version).
    """
    target = str(Path(target).resolve())
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", f'"{target}"',
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F",                    # overwrite if exists
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode == 0:
            print(f"[Startup] Method B (schtasks): task '{TASK_NAME}' created.")
            return True
        err = result.stderr.decode(errors="ignore")
        print(f"[Startup] schtasks error: {err}")
    except Exception as exc:
        print(f"[Startup] schtasks failed: {exc}")
    return False


def _method_b_remove() -> bool:
    """Delete the Task Scheduler task."""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            print(f"[Startup] Method B: task '{TASK_NAME}' removed.")
            return True
    except Exception as exc:
        print(f"[Startup] schtasks remove failed: {exc}")
    return False


def _method_b_exists() -> bool:
    """Check whether the scheduled task is registered."""
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def enable_startup(path_to_jarvis_exe: str | None = None) -> str:
    """
    Register Jarvis for auto-start at Windows login.

    Parameters
    ----------
    path_to_jarvis_exe : str | None
        Full path to Jarvis.exe (or the .py file if running via Python).
        If None, uses the currently running interpreter + __main__ script.

    Returns
    -------
    "method_a" | "method_b" | "failed"
    """
    if path_to_jarvis_exe is None:
        # Best-guess: running as a .py directly or via PyInstaller
        if getattr(sys, "frozen", False):
            path_to_jarvis_exe = sys.executable         # PyInstaller EXE
        else:
            main_script = Path(sys.argv[0]).resolve()
            path_to_jarvis_exe = (
                f'{sys.executable} "{main_script}"'      # python main.py
            )

    # Make sure startup folder exists
    STARTUP_DIR.mkdir(parents=True, exist_ok=True)

    # Try Method A first
    if _method_a_create(str(path_to_jarvis_exe)):
        return "method_a"

    # Try Method B
    if _method_b_create(str(path_to_jarvis_exe)):
        return "method_b"

    print("[Startup] Both registration methods failed.")
    return "failed"


def disable_startup() -> bool:
    """Remove Jarvis from Windows startup (both methods if present)."""
    a = _method_a_remove()
    b = _method_b_remove()
    return a or b


def startup_status() -> str:
    """
    Return the currently active startup registration method.

    Returns
    -------
    "method_a" | "method_b" | "none"
    """
    if SHORTCUT.exists():
        return "method_a"
    if _method_b_exists():
        return "method_b"
    return "none"


# ─────────────────────────────────────────────────────────────────────────────
# CLI quick-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis startup manager")
    parser.add_argument("action", choices=["enable", "disable", "status"])
    parser.add_argument("--exe", help="Path to Jarvis executable", default=None)
    args = parser.parse_args()

    if args.action == "enable":
        method = enable_startup(args.exe)
        print(f"Startup enabled via {method}")
    elif args.action == "disable":
        ok = disable_startup()
        print("Startup removed." if ok else "Nothing to remove.")
    else:
        print(f"Current startup status: {startup_status()}")
