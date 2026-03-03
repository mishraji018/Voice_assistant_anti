
import threading
from typing import Callable, Any, Dict, List

class EventBus:
    """
    Thread-safe Event Bus for JARVIS architecture.
    Handles Pub/Sub communication between decoupled modules.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Subscribe a callback to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def emit(self, event_type: str, data: Any = None):
        """Emit an event with optional data to all subscribers."""
        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()
        
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in callback for {event_type}: {e}")

# Global bus instance for the modular architecture
bus = EventBus()
