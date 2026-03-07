
import sqlite3
import os
from datetime import datetime

# Separate DB for learning as requested
LEARNING_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jarvis_learning.db")
LEARNING_DB_URI = LEARNING_DB_PATH
LEARNING_DB_KWARGS = {}
_LEARNING_KEEPALIVE = None


def _configure_learning_backend():
    global LEARNING_DB_URI, LEARNING_DB_KWARGS, _LEARNING_KEEPALIVE
    try:
        conn = sqlite3.connect(LEARNING_DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS __learning_probe (id INTEGER)")
        conn.commit()
        conn.close()
    except sqlite3.Error:
        LEARNING_DB_URI = "file:jarvis_learning_shared?mode=memory&cache=shared"
        LEARNING_DB_KWARGS = {"uri": True, "check_same_thread": False}
        _LEARNING_KEEPALIVE = sqlite3.connect(LEARNING_DB_URI, **LEARNING_DB_KWARGS)


def _connect_learning_db():
    return sqlite3.connect(LEARNING_DB_URI, **LEARNING_DB_KWARGS)

def init_learning_db():
    """Initialize the learning database."""
    conn = _connect_learning_db()
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
    
    conn = _connect_learning_db()
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
    
    conn = _connect_learning_db()
    cursor = conn.cursor()
    cursor.execute("SELECT intent FROM intent_memory WHERE query = ?", (query,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None

# Initialize on import
_configure_learning_backend()
init_learning_db()
