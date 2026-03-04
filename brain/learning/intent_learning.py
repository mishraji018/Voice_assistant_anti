
import sqlite3
import os
from datetime import datetime

# Separate DB for learning as requested
LEARNING_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jarvis_learning.db")

def init_learning_db():
    """Initialize the learning database."""
    conn = sqlite3.connect(LEARNING_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intent_memory (
            query TEXT PRIMARY KEY,
            intent TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_learned_intent(query: str, intent: str):
    """Save or update a learned intent mapping."""
    if not query or not intent: return
    
    query = query.lower().strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(LEARNING_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO intent_memory (query, intent, timestamp) VALUES (?, ?, ?)",
        (query, intent, timestamp)
    )
    conn.commit()
    conn.close()
    print(f"[Learning] Saved: '{query}' -> {intent}")

def get_learned_intent(query: str) -> str:
    """Retrieve a learned intent for a given query."""
    query = query.lower().strip()
    
    conn = sqlite3.connect(LEARNING_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT intent FROM intent_memory WHERE query = ?", (query,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None

# Initialize on import
init_learning_db()
