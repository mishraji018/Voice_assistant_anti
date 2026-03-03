
import re
from typing import Dict, Any

# Map keywords to intents for rule-based matching
# entities are captured via regex or basic splitting
INTENT_PATTERNS = {
    "WEATHER": [
        r"(?:weather|mausam|aaj ka mausam|temperature|taapmaan)\s*(?:in|me|mein)?\s*(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+(?:weather|mausam|ka mausam)"
    ],
    "OPEN_APP": [

        r"(?:open|start|launch|chalao|kholo)\s+(?P<entity>[\w\s]+)",
        r"(?P<entity>[\w\s]+)\s+(?:kholo|chalo)"
    ],
    "SEARCH_WEB": [
        r"(?:search|google|find|dhundo|pata karo)\s+(?:for|about)?\s*(?P<entity>[\w\s]+)",
        r"(?P<entity>[\w\s]+)\s+(?:search karo|dhundo)"
    ],
    "INFO_QUERY": [
        r"(?:what|who|where|how|when|kya|kab|kaise|kahan)\s+is\s+(?P<entity>[\w\s?]+)",
        r"(?P<entity>[\w\s]+)\s+(?:batao|kya hai)"
    ],
    "CLOSE_WINDOW": [
        r"(?:close|exit|quit|band karo|hatao)\s+(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+(?:band karo)"
    ],
    "SYSTEM_CONTROL": [
        r"(?:shutdown|restart|lock|volume|muted?|awaj|chup)\s+(?P<entity>[\w\s]*)"
    ],
    "SMALL_TALK": [
        r"(?:hello|hi|jarvis|kaise ho|how are you|hey)"
    ]
}

def detect_intent(text: str) -> Dict[str, Any]:
    """
    Detect structured intent and entities from user input.
    """
    text = text.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                entity = match.groupdict().get("entity", "").strip()
                # Clean up entity from question marks etc
                entity = entity.replace("?", "").strip()
                
                return {
                    "intent": intent,
                    "entity": entity,
                    "confidence": 0.9,
                    "original": text
                }
    
    return {
        "intent": "UNKNOWN",
        "entity": "",
        "confidence": 0.0,
        "original": text
    }
