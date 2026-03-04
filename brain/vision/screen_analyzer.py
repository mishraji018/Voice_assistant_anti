
import os
import time
import logging
import pyautogui
from PIL import Image

# Graceful import of pytesseract
try:
    import pytesseract
except ImportError:
    pytesseract = None

logger = logging.getLogger(__name__)

# Default path for Tesseract on Windows
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def capture_screen():
    """Take a screenshot and return the filename."""
    timestamp = int(time.time())
    # Save in temp or project root? Let's use root/screenshots
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "screenshots")
    if not os.path.exists(folder): os.makedirs(folder)
    
    path = os.path.join(folder, f"screen_{timestamp}.png")
    pyautogui.screenshot(path)
    return path

def analyze_screen() -> str:
    """Analyze the screen using OCR and basic pattern matching."""
    if not pytesseract:
        return "Sir, I need 'pytesseract' installed for OCR and computer vision. Par main basic screenshot le sakti hoon."

    try:
        # 1. Capture
        img_path = capture_screen()
        img = Image.open(img_path)
        
        # 2. OCR (Extract Text)
        text = pytesseract.image_to_string(img).strip()
        
        # 3. Simple description
        if not text:
            return "Sir, your screen seems to show mostly images or a blank desktop. I couldn't read any clear text."
        
        # 4. Contextualizing (detect common apps by title/text)
        apps = []
        if "google" in text.lower() or "chrome" in text.lower(): apps.append("Chrome")
        if "github" in text.lower(): apps.append("GitHub")
        if "notepad" in text.lower(): apps.append("Notepad")
        if "code" in text.lower(): apps.append("VS Code")
        
        description = "Sir, I see a screen with some text."
        if apps:
            description = f"Sir, I see {', '.join(apps)} open on your screen."
            
        return f"{description} The text I detected says: '{text[:100]}...'"
        
    except Exception as e:
        logger.error(f"Vision error: {e}")
        return "Sir, screen analyze karne mein kuch error aa rahi hai. Kya aapne Tesseract install kiya hai?"

def get_screen_text() -> str:
    """Fast OCR for reading specific content."""
    if not pytesseract: return "OCR not available."
    try:
        img_path = capture_screen()
        return pytesseract.image_to_string(Image.open(img_path)).strip()
    except:
        return ""
