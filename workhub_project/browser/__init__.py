"""
Browser Automation & Recovery Package for WorkHub Web
"""

from .browser_manager import BrowserManager, get_browser_manager
from .element_resolver import ElementResolver
from .observation_tools import ObservationTools
from .interaction_tools import InteractionTools
from .wait_manager import WaitManager
from .verifier import ActionVerifier
from .recovery_manager import RecoveryManager
from .stuck_detector import StuckDetector
from .session_manager import SessionManager
from .telemetry import TelemetryManager, get_telemetry_manager

__all__ = [
    "BrowserManager",
    "get_browser_manager",
    "ElementResolver",
    "ObservationTools",
    "InteractionTools",
    "WaitManager",
    "ActionVerifier",
    "RecoveryManager",
    "StuckDetector",
    "SessionManager",
    "TelemetryManager",
    "get_telemetry_manager"
]
