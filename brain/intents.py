
import re
from typing import Dict, Any

# Map keywords to intents for rule-based matching
# Priority is determined by order in dictionary
INTENT_PATTERNS = {
    "WEATHER": [
        r"\b(?:weather|mausam|temperature|taapmaan)\b\s*(?:in|me|mein)?\s*(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+\b(?:weather|mausam|ka mausam|temperature)\b"
    ],
    "SYSTEM_CONTROL": [
        r"\b(?:shutdown|restart|reboot|sleep|hibernate|lock|sign out|chup|silent|muted?|volume|awaj)\b\s*(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+\b(?:shutdown|restart|lock)\b"
    ],
    "OPEN_APP": [
        r"\b(?:open|start|launch|chalao|kholo|run)\b\s+(?P<entity>[\w\s]+)",
        r"(?P<entity>[\w\s]+)\s+\b(?:kholo|chalo)\b"
    ],
    "MEDIA_CONTROL": [
        r"\b(?:play|pause|resume|stop music|next|previous|gaana bajao|gaana badlo)\b\s*(?P<entity>[\w\s]*)"
    ],
    "COMPLEX_QUERY": [
        r"\b(?:research|find|analyze|compare|best|top|plan)\b\s*(?:for|about)?\s*(?P<entity>.*)",
        r"(?P<entity>.*)\s+(?:kaisa hai|kaise karein|plan batao|research karo)"
    ],
    "VISION_QUERY": [
        r"\b(?:read|analyze|what is on|show)\b\s+(?:screen|screenshot|desktop|this text)\b",
        r"(?:read screen|what's on my screen|screen analyze karo)"
    ],
    "NOTEPAD_WRITE": [
        r"\b(?:write|type|likho|not down|pen down|typing)\b\s+(?P<entity>.*)\s+(?:in|on|mein|me|ko)\b\s*\b(?:notepad|note pad)\b",
        r"\b(?:notepad|note pad)\b\s*\b(?:me|mein|in|on)\b\s+(?P<entity>.*)\s*\b(?:batao|likho|type karo)\b"
    ],
    "CAPABILITY_QUERY": [
        r"\b(?:can you|kya tum|kya aap|do you know how to|hum kya kya kar sakte)\b\s+(?P<entity>[\w\s]*)"
    ],
    "MEMORY_STORE": [
        r"\b(?:my name is|mera naam|i live in|i am from|i prefer|mujhe pasand hai|mera kaam|my profession is)\b\s*(?P<entity>.*)",
        r"(?P<entity>.*)\s+\b(?:yaad rakho|mera)\b"
    ],
    "MEMORY_QUERY": [
        r"\b(?:what is my name|who am i|mera naam kya hai|where do i live|main kahan rehta hoon|what do i like|mujhe kya pasand hai)\b",
        r"\b(?:do you remember|yaad hai)\b\s+(?P<entity>[\w\s]*)"
    ],
    "BROWSER_SEARCH": [
        r"\b(?:search|google|find)\b\s+(?P<entity>.*)\s+\b(?:on browser|web search|online)\b",
        r"\b(?:browse|open browser and search)\b\s+(?P<entity>.*)"
    ],
    "TASK_CREATE": [
        r"\b(?:remind me to|add task|task add|remind me at)\b\s+(?P<entity>.*)",
        r"(?P<entity>.*)\s+\b(?:ka reminder lagao|yaad dilao)\b"
    ],
    "TASK_LIST": [
        r"\b(?:what are my tasks|show tasks|list tasks|my schedule|agenda|to do list)\b"
    ],
    "WELLNESS_TRACKING": [
        r"\b(?:eat|drank|drink|slept|exercise|workout|walk|running|glasses|water|pani|neend|gym|report|health)\b\s*(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+\b(?:water|glass|hours|minutes|health|routine)\b",
        r"(?:how healthy|health report|how was my day)"
    ],
    "NUTRITION_QUERY": [
        r"\b(?:eat|food|fruit|juice|avoid|khana|kha sakte hain|faydemand|nuksan|parhez)\b\s*(?:during|in|mein|me)?\s*(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+\b(?:good for|bad for|khana chahiye|nahi khana chahiye)\b"
    ],
    "SEARCH_WEB": [
        r"\b(?:search|google|find|dhundo|pata karo|look up)\b\s+(?:for|about)?\s*(?P<entity>[\w\s]+)",
        r"(?P<entity>[\w\s]+)\s+\b(?:search karo|dhundo)\b"
    ],
    "INFO_QUERY": [
        r"\b(?:what|who|where|how|when|kya|kab|kaise|kahan)\b\s+is\s+(?P<entity>[\w\s?]+)",
        r"(?P<entity>[\w\s]+)\s+\b(?:batao|kya hai)\b"
    ],
    "CLOSE_WINDOW": [
        r"\b(?:close|exit|quit|band karo|hatao)\b\s+(?P<entity>[\w\s]*)",
        r"(?P<entity>[\w\s]*)\s+\b(?:band karo)\b"
    ],
    "SMALL_TALK": [
        r"\b(?:hello|hi|jarvis|kaise ho|how are you|hey|namaste|shukriya|thanks)\b"
    ]
}

def detect_intent(text: str) -> Dict[str, Any]:
    """
    Detect structured intent and entities from user input.
    """
    text = text.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            # We use word boundaries \b to avoid partial matches (e.g. 'eat' in 'weather')
            # If the pattern already has \b, re.search handles it.
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
