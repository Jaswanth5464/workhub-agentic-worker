"""
Server-Sent Events (SSE) Telemetry Manager for Browser Automation.
"""

import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List

logger = logging.getLogger(__name__)

class TelemetryManager:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._recent_events: List[Dict[str, Any]] = []
        self._max_recent = 100

    async def emit(self, event_type: str, data: Dict[str, Any] = None, session_id: str = "default"):
        """Emits an SSE event to all connected listeners."""
        payload = {
            "type": event_type,
            "session_id": session_id,
            "timestamp": time.time(),
            "data": data or {}
        }
        
        self._recent_events.append(payload)
        if len(self._recent_events) > self._max_recent:
            self._recent_events.pop(0)
            
        dead_subscribers = []
        for queue in self._subscribers:
            try:
                await queue.put(payload)
            except Exception:
                dead_subscribers.append(queue)
                
        for dead in dead_subscribers:
            if dead in self._subscribers:
                self._subscribers.remove(dead)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Generator for SSE endpoints yielding formatted SSE messages."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        
        # Send recent events immediately for hydration
        for ev in self._recent_events[-10:]:
            yield f"data: {json.dumps(ev)}\n\n"
            
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

_telemetry_instance = TelemetryManager()

def get_telemetry_manager() -> TelemetryManager:
    return _telemetry_instance
