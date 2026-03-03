
class RuntimeState:
    def __init__(self):
        self.last_opened_app = None
        self.action_history = []

    def update_action(self, action: str):
        self.action_history.append(action)
        if len(self.action_history) > 5:
            self.action_history.pop(0)

state = RuntimeState()
