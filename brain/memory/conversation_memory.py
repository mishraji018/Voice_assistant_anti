
import time
from collections import deque
from typing import List, Dict

class ConversationMemory:
    """
    Lightweight conversation memory buffer for JARVIS.
    Stores recent turns and handles inactivity resets.
    """
    def __init__(self, max_length: int = 8, inactivity_limit: int = 600):
        self._buffer = deque(maxlen=max_length)
        self._last_update = time.time()
        self._inactivity_limit = inactivity_limit # 10 minutes default

    def add_turn(self, query: str, response: str):
        """Add a conversation turn (User Query, Jarvis Response)."""
        self._check_inactivity()
        self._buffer.append({
            "query": query,
            "response": response,
            "timestamp": time.time()
        })
        self._last_update = time.time()

    def get_history_string(self) -> str:
        """Format buffer as a string for LLM context."""
        self._check_inactivity()
        if not self._buffer:
            return ""
        
        history = "Previous conversation context:\n"
        for turn in self._buffer:
            history += f"User: {turn['query']}\nJarvis: {turn['response']}\n"
        return history

    def _check_inactivity(self):
        """Reset buffer if quiet for more than inactivity_limit."""
        if time.time() - self._last_update > self._inactivity_limit:
            if self._buffer:
                print("[Memory] Inactivity limit reached. Resetting conversation buffer.")
                self._buffer.clear()

    def clear(self):
        """Force clear memory."""
        self._buffer.clear()

# Global memory singleton
memory = ConversationMemory()
