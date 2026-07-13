import threading
import time
from dataclasses import dataclass

class CancellationToken:
    """Thread-safe cancellation token with a reason string."""
    def __init__(self):
        self._event = threading.Event()
        self._reason = ""

    def cancel(self, reason: str = "USER_INTERRUPTED"):
        self._reason = reason
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

@dataclass
class PipelineContext:
    request_id: str
    session_id: str
    timestamp: float
    user_id: str
    cancel_token: CancellationToken

    @classmethod
    def create(cls, request_id: str):
        return cls(
            request_id=request_id,
            session_id="default_session",
            timestamp=time.time(),
            user_id="local_user",
            cancel_token=CancellationToken()
        )
