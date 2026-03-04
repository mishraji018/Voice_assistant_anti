
import sqlite3
import os
import re
from datetime import datetime

# Point to the existing jarvis_memory.db
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jarvis_memory.db")

class LongTermMemory:
    """
    Handles permanent storage and retrieval of user facts and preferences.
    """
    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        # Fact extraction patterns (Hinglish/English)
        self.save_patterns = [
            (r"(?:my name is|mera naam|i am)\s+(?P<value>[\w\s]+)", "name"),
            (r"(?:i live in|main\s+[\w\s]+\s+me rehta hoon|i am from)\s+(?P<value>[\w\s]+)", "city"),
            (r"(?:i like|i prefer|mujhe\s+[\w\s]+\s+pasand hai|favorite)\s+(?P<value>[\w\s]+)", "preference"),
            (r"(?:i am a|i work as|mera kaam)\s+(?P<value>[\w\s]+)", "profession"),
            (r"(?:my birthday is on|mera janamdin)\s+(?P<value>[\w\s]+)", "birthday")
        ]

        # Fact retrieval patterns
        self.query_patterns = [
            (r"what is my name|mera naam kya hai", "name"),
            (r"where do i live|main kahan rehta hoon", "city"),
            (r"what do i like|mujhe kya pasand hai", "preference"),
            (r"what is my profession|mera kaam kya hai", "profession"),
            (r"when is my birthday|mera janamdin kab hai", "birthday")
        ]

    def process_query(self, text: str) -> str:
        """Analyze text to either store or retrieve a fact."""
        text_lower = text.lower().strip()

        # 1. Check if it's a retrieval query
        for pattern, key in self.query_patterns:
            if re.search(pattern, text_lower):
                val = self.get_fact(key)
                if val:
                    return f"Sir, according to my memory, your {key} is {val}."
                return f"Sir, I don't remember your {key} yet. Aapne bataya nahi."

        # 2. Check if it's a storage query
        for pattern, key in self.save_patterns:
            match = re.search(pattern, text_lower)
            if match:
                value = match.group("value").strip()
                self.save_fact(key, value)
                return f"Got it sir! Maine yaad kar liya hai ki aapka {key} {value} hai."

        return None

    def save_fact(self, key: str, value: str):
        """Save a key-value pair to the database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO memory_store (key, value, timestamp) VALUES (?, ?, ?)",
                (key, value, timestamp)
            )
            conn.commit()
        except Exception as e:
            print(f"[Memory] Error saving fact: {e}")
        finally:
            conn.close()

    def get_fact(self, key: str) -> str:
        """Retrieve a value from the database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM memory_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"[Memory] Error retrieving fact: {e}")
            return None
        finally:
            conn.close()

# Singleton instance
lt_memory = LongTermMemory()
