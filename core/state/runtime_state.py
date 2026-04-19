
import threading


class RuntimeState:
    def __init__(self):
        self.last_opened_app = None
        self.action_history = []
        self._stop_event = threading.Event()
        self.last_checkin_dt = None # Stores date string (YYYY-MM-DD)
        self.last_query = None
        self.last_intent = None
        self.last_activity_time = 0.0 # Timestamp of the last wake-word or response
        self.last_response = None # Stores the text of the last AI response
        self.last_response_use_female = False

    def request_stop(self):
        """Signal all processing threads to stop."""
        self._stop_event.set()

    def clear_stop(self):
        """Clear the stop flag before new processing."""
        self._stop_event.clear()

    def is_stop_requested(self) -> bool:
        """Check if a stop has been requested."""
        return self._stop_event.is_set()

    def update_action(self, action: str):
        self.action_history.append(action)
        if len(self.action_history) > 5:
            self.action_history.pop(0)

state = RuntimeState()
