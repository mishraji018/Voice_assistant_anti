
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jarvis_memory.db")
DB_URI = DB_PATH
DB_CONNECT_KWARGS = {}
_MEMORY_KEEPALIVE = None


def _configure_database_backend():
    global DB_URI, DB_CONNECT_KWARGS, _MEMORY_KEEPALIVE
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS __db_probe (id INTEGER)")
        conn.commit()
        conn.close()
    except sqlite3.Error:
        DB_URI = "file:jarvis_memory_shared?mode=memory&cache=shared"
        DB_CONNECT_KWARGS = {"uri": True, "check_same_thread": False}
        _MEMORY_KEEPALIVE = sqlite3.connect(DB_URI, **DB_CONNECT_KWARGS)


def connect_db():
    return sqlite3.connect(DB_URI, **DB_CONNECT_KWARGS)


_configure_database_backend()

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = connect_db()
    cursor = conn.cursor()

    # 1. Learning Corrections Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mistake TEXT NOT NULL,
            correction TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Activity Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            target_name TEXT NOT NULL,
            target_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wellness_log (
            date TEXT PRIMARY KEY,
            water_glasses INTEGER DEFAULT 0,
            exercise_minutes INTEGER DEFAULT 0,
            sleep_hours REAL DEFAULT 0.0,
            diet_rating INTEGER DEFAULT 0,
            mood TEXT DEFAULT 'neutral'
        )
    ''')

    # 4. Long-Term Memory (Facts/Preferences)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_store (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Productivity (Tasks/Reminders)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks_table (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            time TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"[Database] Initialized at {DB_PATH}")

def log_activity(action_type: str, target_name: str, target_path: str = ""):
    """Log an activity to both SQLite and jarvis.txt."""
    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Save to SQLite
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (action_type, target_name, target_path, timestamp) VALUES (?, ?, ?, ?)",
        (action_type, target_name, target_path, ts_str)
    )
    conn.commit()
    conn.close()

    # 2. Save to logs/jarvis.txt (Simplified for user reading)
    txt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "jarvis.txt")
    log_entry = f"[{ts_str}] → Opened: {target_name} ({action_type})\n"
    with open(txt_path, "a", encoding="utf-8") as f:
        f.write(log_entry)

def cleanup_old_activity():
    """Remove logs older than 24 hours."""
    cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activity_log WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()
    
    # Note: Full jarvis.txt cleanup would require rewriting the file, 
    # usually done on startup or periodically.
    print("[Database] Cleaned up logs older than 24 hours.")

# Only initialize when run directly as a script
if __name__ == "__main__":
    init_db()
