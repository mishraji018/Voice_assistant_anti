import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from brain.infra.database import connect_db


def save_correction(mistake: str, correction: str):
    """Save a user-provided correction to the database."""
    conn = connect_db()
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
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT correction FROM learning_corrections WHERE mistake = ?",
        (query.lower().strip(),)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def _load_intent_learning_module():
    """
    Compatibility bridge:
    Keeps `from brain.learning import intent_learning` working even though
    `brain.learning` is a module file and learned intent logic lives in
    `brain/learning/intent_learning.py`.
    """
    module_path = Path(__file__).parent / "learning" / "intent_learning.py"
    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "brain.learning.intent_learning",
        str(module_path),
    )
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"[Learning] intent_learning load failed: {exc}")
        return None
    return module


intent_learning = _load_intent_learning_module()
if intent_learning is not None:
    sys.modules.setdefault("brain.learning.intent_learning", intent_learning)
else:
    # Keep imports stable even when the optional module cannot be loaded.
    intent_learning = SimpleNamespace(
        get_learned_intent=lambda _query: None,
        save_learned_intent=lambda _query, _intent: None,
    )


def get_learned_intent(query: str):
    """Proxy for learned intent lookup with safe fallback."""
    try:
        return intent_learning.get_learned_intent(query)
    except Exception as exc:
        print(f"[Learning] get_learned_intent failed: {exc}")
        return None


def save_learned_intent(query: str, intent: str):
    """Proxy for learned intent save with safe fallback."""
    try:
        intent_learning.save_learned_intent(query, intent)
    except Exception as exc:
        print(f"[Learning] save_learned_intent failed: {exc}")
