"""
watchdog_launcher.py  –  Crash-recovery wrapper for Jarvis
===========================================================
Launches `tray_icon.py` (or `main.py`) and automatically restarts it
if it exits unexpectedly.  Crash details are written to crash_log.txt.

Usage
-----
    python watchdog_launcher.py              # normal run (with tray)
    python watchdog_launcher.py --no-tray   # raw main.py no tray

How it works
------------
  1. Spawn Jarvis as a subprocess.
  2. Wait for the process to finish.
  3. If exit code == 0 (clean exit) → stop watching; we're done.
  4. Any other exit code (crash) → wait RESTART_DELAY seconds, log the
     crash, then restart (up to MAX_RESTARTS times).

Run on boot via Windows Task Scheduler or Startup folder, targeting
this script (or its compiled .exe) directly — no terminal window needed.
"""

import subprocess
import sys
import time
import logging
import os
import signal
from pathlib import Path
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_RESTARTS   = 10          # give up after this many consecutive crashes
RESTART_DELAY  = 5           # seconds to wait before restarting
SUCCESS_WINDOW = 30          # seconds – if Jarvis ran longer than this,
                             # reset the crash counter (it was healthy)

ROOT_DIR   = Path(__file__).parent.parent
CRASH_LOG  = ROOT_DIR / "crash_log.txt"
USE_TRAY   = "--no-tray" not in sys.argv

# Which script to run
TARGET = ROOT_DIR / ("brain/tray_icon.py" if USE_TRAY else "main.py")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(CRASH_LOG),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Watchdog")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _launch() -> subprocess.Popen:
    """Start Jarvis as a detached subprocess (no console window on Windows)."""
    kwargs = {
        "args": [sys.executable, str(TARGET)],
        "cwd":  str(ROOT_DIR),
    }
    # On Windows, hide the console window
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    return subprocess.Popen(**kwargs)


def _log_crash(proc: subprocess.Popen, attempt: int, elapsed: float) -> None:
    msg = (
        f"Crash #{attempt}: PID={proc.pid} | "
        f"exit_code={proc.returncode} | "
        f"ran_for={elapsed:.1f}s"
    )
    logger.error(msg)
    print(f"[Watchdog] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Main watchdog loop
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Watchdog started. Monitoring: %s", TARGET)
    print(f"[Watchdog] Starting Jarvis ({TARGET.name})…")

    consecutive_crashes = 0

    while True:
        start_time = time.monotonic()
        proc       = _launch()

        logger.info("Jarvis started (PID=%d)", proc.pid)
        print(f"[Watchdog] Jarvis running (PID={proc.pid})")

        try:
            proc.wait()                  # block until child exits
        except KeyboardInterrupt:
            logger.info("Watchdog interrupted by user — terminating Jarvis")
            proc.terminate()
            break

        elapsed   = time.monotonic() - start_time
        exit_code = proc.returncode

        # ── Clean exit ────────────────────────────────────────────────────────
        if exit_code == 0:
            logger.info("Jarvis exited cleanly (ran %.1fs). Watchdog stopping.", elapsed)
            print("[Watchdog] Jarvis exited cleanly. Goodbye.")
            break

        # ── Crash ─────────────────────────────────────────────────────────────
        consecutive_crashes += 1
        _log_crash(proc, consecutive_crashes, elapsed)

        # Reset counter if Jarvis had a healthy run before this crash
        if elapsed > SUCCESS_WINDOW:
            logger.info("Run exceeded success window – resetting crash counter")
            consecutive_crashes = 1

        if consecutive_crashes >= MAX_RESTARTS:
            logger.critical(
                "Max restarts (%d) reached. Watchdog giving up.", MAX_RESTARTS
            )
            print(f"[Watchdog] ❌ Too many crashes ({MAX_RESTARTS}). Giving up.")
            break

        next_restart = RESTART_DELAY * consecutive_crashes  # back-off
        logger.info(
            "Restarting in %ds (attempt %d/%d)…",
            next_restart, consecutive_crashes + 1, MAX_RESTARTS,
        )
        print(
            f"[Watchdog] ⚠ Crash #{consecutive_crashes}. "
            f"Restarting in {next_restart}s…"
        )
        time.sleep(next_restart)


if __name__ == "__main__":
    main()
