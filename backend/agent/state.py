from enum import Enum
from typing import List

class AgentState(str, Enum):
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    DONE = "DONE"
    FAILED = "FAILED"
    NEEDS_USER = "NEEDS_USER"
    CANCELLED = "CANCELLED"

class StateMachine:
    def __init__(self):
        self.state = AgentState.UNDERSTANDING
        self.history: List[AgentState] = []
        self._emit_cb = None
        
    def set_emitter(self, cb):
        self._emit_cb = cb

    async def transition(self, new_state: AgentState):
        if self.state != new_state:
            self.history.append(self.state)
            self.state = new_state
            if self._emit_cb:
                await self._emit_cb({
                    "type": "state",
                    "state": self.state.value
                })
