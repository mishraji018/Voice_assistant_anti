
import sqlite3
import os
from brain.infra.database import DB_PATH

def save_correction(mistake: str, correction: str):
    """Save a user-provided correction to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO learning_corrections (mistake, correction) VALUES (?, ?)",
        (mistake.lower().strip(), correction.lower().strip())
    )
    conn.commit()
    conn.close()
    print(f"[Learning] Saved correction for '{mistake}' -> '{correction}'")

def get_correction(query: str) -> str:
    """Check if we have a known correction for this exact query."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT correction FROM learning_corrections WHERE mistake = ?",
        (query.lower().strip(),)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
