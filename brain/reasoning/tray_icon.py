"""
tray_icon.py  –  System-tray launcher for Jarvis
==================================================
Runs Jarvis in the background with a pystray icon that reflects the
current assistant state (IDLE / LISTENING / SPEAKING / WAKE).

Usage
-----
    python tray_icon.py          # launches Jarvis with tray icon
    (or use the compiled .exe)

Dependencies
------------
    pip install pystray pillow

Integration
-----------
    Import TrayManager and pass its set_state() to JarvisUI instead of
    the Default UI state machine, OR run this as the top-level entry point.
"""

import threading
import sys
import time
import subprocess
import os
import logging
from pathlib import Path

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw, ImageFont
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    print("[Tray] pystray / pillow not installed. Run: pip install pystray pillow")

# ── Logging setup ─────────────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "jarvis_tray.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("JarvisTray")

# ── State → colour mapping ────────────────────────────────────────────────────
STATE_COLORS = {
    "IDLE":      "#4A90D9",   # calm blue
    "LISTENING": "#27AE60",   # green  – mic open
    "SPEAKING":  "#E67E22",   # orange – speaking
    "WAKE":      "#9B59B6",   # purple – wake confirmed
    "ERROR":     "#E74C3C",   # red    – crashed / error
}

ICON_SIZE = 64   # pixels (will be shown small in tray anyway)


# ─────────────────────────────────────────────────────────────────────────────
# Icon generation
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' to (R, G, B)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _make_icon_image(state: str) -> "Image.Image":
    """
    Draw a filled circle whose colour reflects the current state.
    Returns a PIL Image (RGBA, ICON_SIZE × ICON_SIZE).
    """
    color = STATE_COLORS.get(state, STATE_COLORS["IDLE"])
    rgb   = _hex_to_rgb(color)

    img  = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer circle
    margin = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=rgb + (255,),
    )

    # Inner 'J' letter — fall back to a dot if default font is missing
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()

    draw.text(
        (ICON_SIZE // 2, ICON_SIZE // 2),
        "J",
        fill=(255, 255, 255, 255),
        font=font,
        anchor="mm",
    )

    return img


# ─────────────────────────────────────────────────────────────────────────────
# TrayManager
# ─────────────────────────────────────────────────────────────────────────────

class TrayManager:
    """
    Manages the pystray icon.  Call set_state() from any thread.

    Parameters
    ----------
    on_exit    : callable – called when the user picks "Exit Jarvis"
    on_restart : callable – called when the user picks "Restart Jarvis"
    log_path   : Path     – path to the log file to open
    """

    def __init__(
        self,
        on_exit=None,
        on_restart=None,
        log_path: Path | None = None,
    ):
        self._on_exit    = on_exit    or (lambda: os._exit(0))
        self._on_restart = on_restart or self._default_restart
        self._log_path   = log_path   or LOG_FILE
        self._state      = "IDLE"
        self._icon       = None
        self._lock       = threading.Lock()

        if not PYSTRAY_AVAILABLE:
            logger.warning("pystray unavailable – tray icon disabled")
            return

        self._build_icon()

    # ── Build / rebuild icon ─────────────────────────────────────────────────

    def _build_icon(self):
        menu = pystray.Menu(
            item("Jarvis – Idle",         self._noop, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Open logs",             self._open_logs),
            item("Restart Jarvis",        self._restart),
            pystray.Menu.SEPARATOR,
            item("Exit Jarvis",           self._exit),
        )
        self._icon = pystray.Icon(
            name="Jarvis",
            icon=_make_icon_image("IDLE"),
            title="Jarvis Assistant – Idle",
            menu=menu,
        )

    # ── State management ─────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """
        Update the tray icon to reflect a new assistant state.
        Thread-safe.  State should be one of IDLE / LISTENING / SPEAKING / WAKE / ERROR.
        """
        with self._lock:
            if state == self._state:
                return
            self._state = state

        state_labels = {
            "IDLE":      "Idle",
            "LISTENING": "Listening…",
            "SPEAKING":  "Speaking…",
            "WAKE":      "Activated!",
            "ERROR":     "Error",
        }
        label = state_labels.get(state, state)

        if self._icon and PYSTRAY_AVAILABLE:
            self._icon.icon  = _make_icon_image(state)
            self._icon.title = f"Jarvis Assistant – {label}"

        logger.info("State → %s", state)

    # ── Run tray (call from a daemon thread) ─────────────────────────────────

    def run(self) -> None:
        """Start the pystray event loop (blocking).  Run in its own thread."""
        if self._icon and PYSTRAY_AVAILABLE:
            logger.info("Tray icon started")
            self._icon.run()

    def run_in_thread(self) -> threading.Thread:
        """Convenience – launch the tray loop in a daemon thread."""
        t = threading.Thread(target=self.run, name="JarvisTray", daemon=True)
        t.start()
        return t

    # ── Menu callbacks ───────────────────────────────────────────────────────

    def _noop(self, icon, query):
        pass

    def _exit(self, icon, query):
        logger.info("Exit requested from tray menu")
        icon.stop()
        self._on_exit()

    def _restart(self, icon, query):
        logger.info("Restart requested from tray menu")
        icon.stop()
        self._on_restart()

    def _open_logs(self, icon, query):
        os.startfile(str(self._log_path))

    def _default_restart(self):
        """Re-launch this process and exit the current one."""
        python = sys.executable
        script = Path(__file__).parent.parent / "main.py"
        subprocess.Popen([python, str(script)], creationflags=subprocess.DETACHED_PROCESS)
        os._exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone entry point:  python tray_icon.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Import Jarvis main loop and wire the tray manager to it
    import importlib.util, pathlib

    tray = TrayManager()

    # Monkey-patch JarvisUI so tray icon reflects state changes
    try:
        from ui.visual_ui import JarvisUI

        class TrayBridgedUI(JarvisUI):
            """Subclass that also updates the tray icon on every state change."""
            def set_state(self, state: str):
                super().set_state(state)
                tray.set_state(state)

        # Replace the class in the module so main.py picks it up
        from ui import visual_ui
        visual_ui.JarvisUI = TrayBridgedUI
    except ImportError:
        pass

    # Start tray icon in background
    tray.run_in_thread()

    # Start Jarvis main loop (blocks until exit)
    try:
        # Note: When running tray_icon directly, we need to ensure main is importable
        # Since we run with -m main usually, this standalone block is for dev.
        import main
        main.run_jarvis()
    except Exception as e:
        logger.exception("Jarvis crashed: %s", e)
        tray.set_state("ERROR")
        time.sleep(3)
    finally:
        os._exit(0)
