"""
jarvis_control.py  –  Mouse and keyboard control for Jarvis
============================================================
Allows Jarvis to operate the desktop like a human:
  • Move mouse smoothly
  • Click, double-click, right-click
  • Type text with human-speed delays
  • Scroll up/down
  • Press hotkeys
  • Click UI elements found by jarvis_vision

Dependencies:
    pip install pyautogui

Public API
----------
    from jarvis_control import ctrl

    ctrl.click(x, y)
    ctrl.type_text("hello world")
    ctrl.scroll_down(3)
    ctrl.press_key("ctrl+c")
    ctrl.click_element("login button")   # uses vision to find it
"""

import time
import threading

# ── Safety guard ──────────────────────────────────────────────────────────────
# pyautogui has a FAILSAFE: move mouse to top-left corner to abort.
_PYAUTOGUI_OK = False
try:
    import pyautogui
    pyautogui.FAILSAFE   = True          # enable corner-abort safety
    pyautogui.PAUSE      = 0.08         # small natural pause between actions
    _PYAUTOGUI_OK        = True
except ImportError:
    print("[Control] pyautogui not installed — control commands disabled.")


class JarvisControl:
    """
    Human-like desktop control via pyautogui.
    All methods fail gracefully if pyautogui is unavailable.
    """

    def __init__(self):
        self._lock = threading.Lock()

    def _check(self) -> bool:
        if not _PYAUTOGUI_OK:
            print("[Control] pyautogui not available.")
            return False
        return True

    # ── Mouse movement ────────────────────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float = 0.4) -> bool:
        """Move mouse to (x, y) with smooth human-like motion."""
        if not self._check():
            return False
        try:
            pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            return True
        except Exception as exc:
            print(f"[Control] move_to error: {exc}")
            return False

    def click(self, x: int, y: int, button: str = "left", delay: float = 0.1) -> bool:
        """Click at (x, y). button = 'left' | 'right' | 'middle'."""
        if not self._check():
            return False
        try:
            with self._lock:
                pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeInOutQuad)
                time.sleep(delay)
                pyautogui.click(x, y, button=button)
                print(f"[Control] Clicked ({x}, {y}) [{button}]")
            return True
        except Exception as exc:
            print(f"[Control] click error: {exc}")
            return False

    def double_click(self, x: int, y: int) -> bool:
        """Double-click at (x, y)."""
        if not self._check():
            return False
        try:
            with self._lock:
                pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeInOutQuad)
                time.sleep(0.1)
                pyautogui.doubleClick(x, y)
                print(f"[Control] Double-clicked ({x}, {y})")
            return True
        except Exception as exc:
            print(f"[Control] double_click error: {exc}")
            return False

    def right_click(self, x: int, y: int) -> bool:
        """Right-click at (x, y)."""
        return self.click(x, y, button="right")

    # ── Keyboard ─────────────────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.04) -> bool:
        """
        Type text at the current cursor position.
        interval: seconds between keystrokes (simulates human typing speed).
        """
        if not self._check():
            return False
        try:
            with self._lock:
                pyautogui.typewrite(text, interval=interval)
                print(f"[Control] Typed: {text!r}")
            return True
        except Exception as exc:
            # typewrite fails on non-ASCII; fall back to pyperclip paste
            try:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                print(f"[Control] Pasted (clipboard): {text!r}")
                return True
            except Exception as exc2:
                print(f"[Control] type_text error: {exc2}")
                return False

    def press_key(self, key_combo: str) -> bool:
        """
        Press a key or hotkey combination.
        Examples: "enter", "ctrl+c", "alt+f4", "ctrl+shift+esc"
        """
        if not self._check():
            return False
        try:
            keys = [k.strip() for k in key_combo.lower().split("+")]
            with self._lock:
                if len(keys) == 1:
                    pyautogui.press(keys[0])
                else:
                    pyautogui.hotkey(*keys)
                print(f"[Control] Pressed: {key_combo}")
            return True
        except Exception as exc:
            print(f"[Control] press_key error: {exc}")
            return False

    # ── Scroll ────────────────────────────────────────────────────────────────

    def scroll_down(self, clicks: int = 3) -> bool:
        """Scroll down by `clicks` units (negative = up)."""
        if not self._check():
            return False
        try:
            pyautogui.scroll(-clicks * 100)
            print(f"[Control] Scrolled down {clicks}")
            return True
        except Exception as exc:
            print(f"[Control] scroll error: {exc}")
            return False

    def scroll_up(self, clicks: int = 3) -> bool:
        """Scroll up by `clicks` units."""
        return self.scroll_down(-clicks)

    # ── Search box helper ─────────────────────────────────────────────────────

    def type_in_search(self, query: str) -> bool:
        """
        Click the center-top of screen (typical browser address bar / search box)
        and type a query. Works well for browser searches.
        """
        if not self._check():
            return False
        try:
            import pyautogui as pg
            w, h = pg.size()
            # Click address bar area (top center)
            self.click(w // 2, 60)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")   # select all existing text
            time.sleep(0.1)
            self.type_text(query)
            time.sleep(0.1)
            self.press_key("enter")
            return True
        except Exception as exc:
            print(f"[Control] type_in_search error: {exc}")
            return False

    # ── Vision-integrated click ───────────────────────────────────────────────

    def click_element(self, label: str) -> bool:
        """
        Find a UI element on screen by label (using jarvis_vision) and click it.
        Returns True if element was found and clicked.
        """
        try:
            from jarvis_vision import vision
            pos = vision.find_element(label)
            if pos is None:
                pos = vision.find_element_fuzzy(label)
            if pos:
                return self.click(pos[0], pos[1])
            print(f"[Control] Element '{label}' not found on screen.")
            return False
        except Exception as exc:
            print(f"[Control] click_element error: {exc}")
            return False

    # ── Compound actions ──────────────────────────────────────────────────────

    def select_all_and_copy(self) -> bool:
        """Select all text in current element and copy to clipboard."""
        ok  = self.press_key("ctrl+a")
        ok &= self.press_key("ctrl+c")
        time.sleep(0.2)
        return ok

    def open_new_tab(self) -> bool:
        """Open a new browser tab."""
        return self.press_key("ctrl+t")

    def close_tab(self) -> bool:
        """Close current browser tab."""
        return self.press_key("ctrl+w")

    def go_to_url(self, url: str) -> bool:
        """Navigate browser to a URL via address bar."""
        ok = self.press_key("ctrl+l")          # focus address bar
        time.sleep(0.2)
        ok &= self.type_text(url)
        ok &= self.press_key("enter")
        return ok


# ── Module singleton ──────────────────────────────────────────────────────────
ctrl = JarvisControl()
