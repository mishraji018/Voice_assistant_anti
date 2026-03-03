"""
jarvis_vision.py  –  Screen reading and OCR for Jarvis
=======================================================
Gives Jarvis the ability to "see" the screen like a human.

Capabilities:
  • Capture full or region screenshot
  • OCR via pytesseract to extract visible text
  • Detect UI elements: buttons, headings, links
  • Spoken-friendly output for Jarvis to read aloud

Dependencies:
    pip install pytesseract pillow pyautogui
    # Also install Tesseract binary:
    # https://github.com/UB-Mannheim/tesseract/wiki  (Windows installer)
    # Default install path: C:/Program Files/Tesseract-OCR/tesseract.exe

Public API
----------
    from jarvis_vision import JarvisVision

    vision = JarvisVision()
    text   = vision.read_screen()                # full screen OCR
    elem   = vision.find_element("login button") # locate element by label
    summary = vision.describe_screen()           # spoken summary
"""

import re
import threading
from pathlib import Path
from typing import Optional

# ── Tesseract setup ───────────────────────────────────────────────────────────
_TESS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def _configure_tesseract():
    try:
        import pytesseract
        for p in _TESS_PATHS:
            if Path(p).exists():
                pytesseract.pytesseract.tesseract_cmd = p
                return True
        # Try PATH as last resort
        return True
    except ImportError:
        return False


_TESS_OK = _configure_tesseract()


class JarvisVision:
    """
    Screen reading module using PIL screenshots + Tesseract OCR.
    Fails gracefully if tesseract / pillow / pyautogui are not installed.
    """

    def __init__(self):
        self._last_text: str = ""
        self._lock = threading.Lock()

    # ── Core OCR ─────────────────────────────────────────────────────────────

    def capture(self, region=None):
        """
        Take a screenshot and return a PIL Image.
        region: (left, top, width, height) or None for full screen.
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=region)
            return screenshot
        except Exception as exc:
            print(f"[Vision] Screenshot failed: {exc}")
            return None

    def read_screen(self, region=None) -> str:
        """
        Capture screen (or region) and return all visible text via OCR.
        Returns '' if OCR fails.
        """
        if not _TESS_OK:
            return "[Vision] pytesseract not installed."
        img = self.capture(region)
        if img is None:
            return ""
        try:
            import pytesseract
            text = pytesseract.image_to_string(img, lang="eng+hin")
            with self._lock:
                self._last_text = text
            return text.strip()
        except Exception as exc:
            print(f"[Vision] OCR error: {exc}")
            return ""

    def read_screen_spoken(self, region=None) -> str:
        """
        Read screen and return a clean, spoken-friendly version.
        Strips extra whitespace and empty lines.
        """
        raw = self.read_screen(region)
        if not raw:
            return "I couldn't read anything on the screen."
        # Clean up noise
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if not lines:
            return "The screen appears to be empty."
        # Keep first 15 meaningful lines to avoid overly long responses
        spoken = ". ".join(lines[:15])
        return f"Here is what I see on the screen: {spoken}"

    # ── Element detection ─────────────────────────────────────────────────────

    def find_element(self, label: str, region=None):
        """
        Search for a UI element containing `label` text on screen.
        Returns (x, y) center coordinates or None if not found.

        Uses pytesseract image_to_data with bounding box info.
        """
        if not _TESS_OK:
            return None
        img = self.capture(region)
        if img is None:
            return None
        try:
            import pytesseract
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, lang="eng+hin"
            )
            label_l = label.lower()
            n = len(data["text"])
            for i in range(n):
                word = data["text"][i].strip().lower()
                if not word:
                    continue
                if label_l in word or word in label_l:
                    # Build bounding box center
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    print(f"[Vision] Found '{label}' at ({x}, {y})")
                    return (x, y)
        except Exception as exc:
            print(f"[Vision] find_element error: {exc}")
        return None

    def find_element_fuzzy(self, label: str, region=None):
        """
        Find element using fuzzy matching (handles partial/approximate labels).
        Returns (x, y) or None.
        """
        if not _TESS_OK:
            return None
        img = self.capture(region)
        if img is None:
            return None
        try:
            import pytesseract
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, lang="eng+hin"
            )
            label_l = label.lower().split()
            best_score = 0
            best_pos = None
            # Group words into lines
            n = len(data["text"])
            for i in range(n):
                word = data["text"][i].strip().lower()
                if not word:
                    continue
                # Score: how many label words appear in this word
                score = sum(1 for lw in label_l if lw in word)
                if score > best_score:
                    best_score = score
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    best_pos = (x, y)
            if best_pos and best_score >= 1:
                print(f"[Vision] Fuzzy found near '{label}' at {best_pos}")
                return best_pos
        except Exception as exc:
            print(f"[Vision] find_element_fuzzy error: {exc}")
        return None

    # ── Screen description ────────────────────────────────────────────────────

    def describe_screen(self) -> str:
        """
        Take a screenshot and produce a concise spoken description.
        Detects headings, buttons, and links based on common patterns.
        """
        raw = self.read_screen()
        if not raw:
            return "I cannot see the screen clearly right now."

        lines  = [l.strip() for l in raw.splitlines() if l.strip()]
        result = []

        # Heuristic: lines in ALL CAPS are likely headings or buttons
        headings = [l for l in lines if l.isupper() and 3 < len(l) < 60]
        links    = [l for l in lines if re.search(r"https?://|www\.", l, re.I)]
        buttons  = [l for l in lines
                    if any(b in l.lower() for b in
                           ["submit", "login", "sign in", "click", "buy",
                            "download", "ok", "cancel", "yes", "no", "next",
                            "back", "close", "search", "send"])]

        if headings:
            result.append("I see headings: " + ", ".join(headings[:3]))
        if buttons:
            result.append("There are buttons: " + ", ".join(set(buttons[:4])))
        if links:
            result.append("I see links on the page.")

        # General text summary (first 8 content lines)
        content = [l for l in lines if len(l) > 10][:8]
        if content:
            result.append("The main content reads: " + ". ".join(content))

        return " ".join(result) if result else "I see some content but cannot summarize it clearly."

    def get_last_text(self) -> str:
        """Return the last OCR'd screen text (cached from previous read)."""
        with self._lock:
            return self._last_text


# ── Module singleton ──────────────────────────────────────────────────────────
vision = JarvisVision()
