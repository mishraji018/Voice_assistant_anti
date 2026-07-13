
import threading
from core.state.state_machine import SystemState

class RuntimeState:
    def __init__(self):
        self._lock = threading.RLock()
        
        # Protected state variables
        self._current_state = SystemState.IDLE
        self._last_opened_app = None
        self._action_history = []
        self._stop_event = threading.Event()
        self._last_checkin_dt = None # Stores date string (YYYY-MM-DD)
        self._last_query = None
        self._last_intent = None
        self._last_activity_time = 0.0 # Timestamp of the last wake-word or response
        self._last_response = None # Stores the text of the last AI response
        self._last_response_use_female = False
        
        # We define properties below to safely read/write these with the lock.

    @property
    def current_state(self) -> SystemState:
        with self._lock: return self._current_state

    @current_state.setter
    def current_state(self, val: SystemState):
        with self._lock: self._current_state = val

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
        with self._lock:
            self._action_history.append(action)
            if len(self._action_history) > 5:
                self._action_history.pop(0)

    @property
    def last_activity_time(self):
        with self._lock: return self._last_activity_time

    @last_activity_time.setter
    def last_activity_time(self, val):
        with self._lock: self._last_activity_time = val

    @property
    def last_response(self):
        with self._lock: return self._last_response

    @last_response.setter
    def last_response(self, val):
        with self._lock: self._last_response = val

    @property
    def last_response_use_female(self):
        with self._lock: return self._last_response_use_female

    @last_response_use_female.setter
    def last_response_use_female(self, val):
        with self._lock: self._last_response_use_female = val

    @property
    def last_query(self):
        with self._lock: return self._last_query

    @last_query.setter
    def last_query(self, val):
        with self._lock: self._last_query = val

    @property
    def last_intent(self):
        with self._lock: return self._last_intent

    @last_intent.setter
    def last_intent(self, val):
        with self._lock: self._last_intent = val

    @property
    def last_checkin_dt(self):
        with self._lock: return self._last_checkin_dt

    @last_checkin_dt.setter
    def last_checkin_dt(self, val):
        with self._lock: self._last_checkin_dt = val

state = RuntimeState()
